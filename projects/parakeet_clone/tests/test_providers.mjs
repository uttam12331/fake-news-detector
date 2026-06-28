// Run with: node tests/test_providers.mjs
import assert from "node:assert";
import {
  buildAnthropicRequest,
  buildOpenAIRequest,
  buildHeaders,
  extractDelta,
  streamChat,
} from "../app/static/providers.js";

let passed = 0;
function test(name, fn) {
  return fn().then(
    () => {
      passed++;
      console.log("ok -", name);
    },
    (e) => {
      console.error("FAIL -", name);
      console.error(e);
      process.exitCode = 1;
    }
  );
}

const img = { mediaType: "image/jpeg", base64: "AAAA" };

await test("anthropic request: images precede text, stream + system set", async () => {
  const req = buildAnthropicRequest({
    model: "claude-sonnet-4-6",
    system: "be brief",
    history: [{ role: "user", text: "hi" }, { role: "assistant", text: "hello" }],
    userText: "what is this?",
    images: [img],
    maxTokens: 512,
  });
  assert.equal(req.model, "claude-sonnet-4-6");
  assert.equal(req.stream, true);
  assert.equal(req.max_tokens, 512);
  assert.equal(req.system, "be brief");
  // history (2) + current user (1)
  assert.equal(req.messages.length, 3);
  const last = req.messages[2];
  assert.equal(last.role, "user");
  assert.equal(last.content[0].type, "image");
  assert.equal(last.content[0].source.media_type, "image/jpeg");
  assert.equal(last.content[1].type, "text");
  assert.equal(last.content[1].text, "what is this?");
});

await test("anthropic request: no system key when absent", async () => {
  const req = buildAnthropicRequest({ model: "m", userText: "hey" });
  assert.ok(!("system" in req));
});

await test("openai request: system first, image as data URL", async () => {
  const req = buildOpenAIRequest({
    model: "gpt-4o",
    system: "sys",
    userText: "describe",
    images: [img],
  });
  assert.equal(req.messages[0].role, "system");
  assert.equal(req.messages[0].content, "sys");
  const userMsg = req.messages[req.messages.length - 1];
  assert.equal(userMsg.content[0].type, "text");
  assert.equal(userMsg.content[1].type, "image_url");
  assert.ok(userMsg.content[1].image_url.url.startsWith("data:image/jpeg;base64,AAAA"));
});

await test("headers: anthropic uses x-api-key + browser-access flag", async () => {
  const h = buildHeaders("anthropic", "sk-ant-x");
  assert.equal(h["x-api-key"], "sk-ant-x");
  assert.equal(h["anthropic-dangerous-direct-browser-access"], "true");
  assert.equal(h["anthropic-version"], "2023-06-01");
});

await test("headers: openai uses bearer auth", async () => {
  const h = buildHeaders("openai", "sk-x");
  assert.equal(h.authorization, "Bearer sk-x");
});

await test("extractDelta: anthropic text_delta + openai delta", async () => {
  assert.equal(
    extractDelta("anthropic", { type: "content_block_delta", delta: { type: "text_delta", text: "Hi" } }),
    "Hi"
  );
  assert.equal(extractDelta("anthropic", { type: "message_start" }), "");
  assert.equal(extractDelta("openai", { choices: [{ delta: { content: "Yo" } }] }), "Yo");
  assert.equal(extractDelta("openai", { choices: [{ delta: {} }] }), "");
});

// Mock streaming response: build a fake SSE stream and feed it through streamChat.
function mockFetch(sseLines) {
  const body = sseLines.join("\n") + "\n";
  const bytes = new TextEncoder().encode(body);
  let sent = false;
  return async () => ({
    ok: true,
    body: {
      getReader: () => ({
        read: async () => {
          if (sent) return { done: true };
          sent = true;
          return { done: false, value: bytes };
        },
      }),
    },
  });
}

await test("streamChat: assembles anthropic stream text", async () => {
  const lines = [
    'data: {"type":"message_start"}',
    'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"Hello"}}',
    'data: {"type":"content_block_delta","delta":{"type":"text_delta","text":", world"}}',
    'data: {"type":"message_stop"}',
  ];
  const chunks = [];
  const full = await streamChat(
    { provider: "anthropic", apiKey: "k", model: "m", userText: "hi" },
    (c) => chunks.push(c),
    mockFetch(lines)
  );
  assert.equal(full, "Hello, world");
  assert.deepEqual(chunks, ["Hello", ", world"]);
});

await test("streamChat: assembles openai stream and ignores [DONE]", async () => {
  const lines = [
    'data: {"choices":[{"delta":{"content":"Par"}}]}',
    'data: {"choices":[{"delta":{"content":"akeet"}}]}',
    "data: [DONE]",
  ];
  const full = await streamChat(
    { provider: "openai", apiKey: "k", model: "gpt-4o", userText: "hi" },
    null,
    mockFetch(lines)
  );
  assert.equal(full, "Parakeet");
});

await test("streamChat: throws on missing key", async () => {
  await assert.rejects(
    () => streamChat({ provider: "anthropic", apiKey: "", userText: "x" }, null, mockFetch([])),
    /No API key/
  );
});

await test("streamChat: surfaces HTTP error body", async () => {
  const failFetch = async () => ({
    ok: false,
    status: 401,
    json: async () => ({ error: { message: "bad key" } }),
  });
  await assert.rejects(
    () => streamChat({ provider: "anthropic", apiKey: "k", model: "m", userText: "x" }, null, failFetch),
    /401/
  );
});

console.log(`\n${passed} checks passed.`);
