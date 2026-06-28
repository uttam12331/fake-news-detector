// LLM provider abstraction. Supports Anthropic (Claude) and OpenAI, with
// streaming and multimodal (image) input. The user's API key lives only in
// the browser (localStorage) and is sent directly to the chosen provider.

export const PROVIDERS = {
  anthropic: {
    label: "Claude (Anthropic)",
    endpoint: "https://api.anthropic.com/v1/messages",
    models: [
      { id: "claude-opus-4-8", label: "Claude Opus 4.8 (most capable)" },
      { id: "claude-sonnet-4-6", label: "Claude Sonnet 4.6 (fast, balanced)" },
      { id: "claude-haiku-4-5-20251001", label: "Claude Haiku 4.5 (fastest)" },
    ],
    keyHint: "sk-ant-...",
  },
  openai: {
    label: "OpenAI (GPT)",
    endpoint: "https://api.openai.com/v1/chat/completions",
    models: [
      { id: "gpt-4o", label: "GPT-4o (multimodal)" },
      { id: "gpt-4o-mini", label: "GPT-4o mini (fast, cheap)" },
    ],
    keyHint: "sk-...",
  },
};

// An "image" is { mediaType: "image/jpeg", base64: "<no prefix>" }.

export function buildAnthropicRequest({ model, system, history, userText, images, maxTokens = 1024 }) {
  const content = [];
  for (const img of images || []) {
    content.push({
      type: "image",
      source: { type: "base64", media_type: img.mediaType, data: img.base64 },
    });
  }
  if (userText) content.push({ type: "text", text: userText });

  const messages = [];
  for (const turn of history || []) {
    messages.push({ role: turn.role, content: turn.text });
  }
  messages.push({ role: "user", content });

  return {
    model,
    max_tokens: maxTokens,
    stream: true,
    ...(system ? { system } : {}),
    messages,
  };
}

export function buildOpenAIRequest({ model, system, history, userText, images, maxTokens = 1024 }) {
  const messages = [];
  if (system) messages.push({ role: "system", content: system });
  for (const turn of history || []) {
    messages.push({ role: turn.role, content: turn.text });
  }

  const content = [];
  if (userText) content.push({ type: "text", text: userText });
  for (const img of images || []) {
    content.push({
      type: "image_url",
      image_url: { url: `data:${img.mediaType};base64,${img.base64}` },
    });
  }
  messages.push({ role: "user", content });

  return {
    model,
    max_tokens: maxTokens,
    stream: true,
    messages,
  };
}

export function buildHeaders(provider, apiKey) {
  if (provider === "anthropic") {
    return {
      "content-type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
      // Required for calling the API directly from a browser.
      "anthropic-dangerous-direct-browser-access": "true",
    };
  }
  return {
    "content-type": "application/json",
    authorization: `Bearer ${apiKey}`,
  };
}

// Pull incremental text out of one parsed SSE JSON object, per provider.
export function extractDelta(provider, obj) {
  if (provider === "anthropic") {
    if (obj.type === "content_block_delta" && obj.delta && obj.delta.type === "text_delta") {
      return obj.delta.text;
    }
    return "";
  }
  // openai
  const choice = obj.choices && obj.choices[0];
  return (choice && choice.delta && choice.delta.content) || "";
}

// Stream a completion. Calls onDelta(textChunk) as tokens arrive.
// Returns the full assembled text. Throws on HTTP / network error.
export async function streamChat(
  { provider, apiKey, model, system, history, userText, images, maxTokens },
  onDelta,
  fetchImpl = fetch
) {
  const cfg = PROVIDERS[provider];
  if (!cfg) throw new Error(`Unknown provider: ${provider}`);
  if (!apiKey) throw new Error("No API key set. Open Settings and paste your key.");

  const body =
    provider === "anthropic"
      ? buildAnthropicRequest({ model, system, history, userText, images, maxTokens })
      : buildOpenAIRequest({ model, system, history, userText, images, maxTokens });

  const res = await fetchImpl(cfg.endpoint, {
    method: "POST",
    headers: buildHeaders(provider, apiKey),
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    let detail = "";
    try {
      detail = JSON.stringify(await res.json());
    } catch (_) {
      detail = await res.text().catch(() => "");
    }
    throw new Error(`${cfg.label} error ${res.status}: ${detail.slice(0, 400)}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let full = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop(); // keep partial last line

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data:")) continue;
      const data = trimmed.slice(5).trim();
      if (!data || data === "[DONE]") continue;
      let obj;
      try {
        obj = JSON.parse(data);
      } catch (_) {
        continue;
      }
      const chunk = extractDelta(provider, obj);
      if (chunk) {
        full += chunk;
        if (onDelta) onDelta(chunk);
      }
    }
  }
  return full;
}
