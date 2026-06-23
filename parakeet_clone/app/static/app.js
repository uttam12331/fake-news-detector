import { PROVIDERS, streamChat } from "./providers.js";
import { LiveTranscriber, isSupported as sttSupported } from "./transcribe.js";
import { captureScreenshot, extractVideoFrames, AudioRecorder } from "./capture.js";

// ---------------------------------------------------------------------------
// Settings (persisted in the browser only)
// ---------------------------------------------------------------------------
const LS = {
  get: (k, d) => localStorage.getItem("cl_" + k) ?? d,
  set: (k, v) => localStorage.setItem("cl_" + k, v),
};

const PERSONAS = {
  interview: {
    label: "Interview Copilot",
    prompt:
      "You are a real-time interview copilot. The user is in a live interview. " +
      "Given the interviewer's question (transcribed) and any screenshots for context, " +
      "give a concise, confident, well-structured answer the user can say out loud. " +
      "Lead with the direct answer, then 2-4 supporting points. Keep it natural and brief.",
  },
  meeting: {
    label: "Meeting Assistant",
    prompt:
      "You are a meeting assistant. Summarise what was asked, surface key points, " +
      "and suggest a clear, professional response or next step. Be concise.",
  },
  sales: {
    label: "Sales Call Copilot",
    prompt:
      "You are a sales-call copilot. Given the prospect's question, suggest a persuasive, " +
      "honest response that handles objections and moves the deal forward. Be concise and human.",
  },
  general: {
    label: "General Q&A",
    prompt: "You are a helpful, knowledgeable assistant. Answer clearly and concisely.",
  },
};

const state = {
  provider: LS.get("provider", "anthropic"),
  model: LS.get("model", ""),
  apiKey: LS.get("apikey", ""),
  personaKey: LS.get("persona", "interview"),
  systemPrompt: LS.get("systemPrompt", PERSONAS.interview.prompt),
  notes: LS.get("notes", ""),
  maxTokens: parseInt(LS.get("maxTokens", "1024"), 10),
  contextImages: [],
  transcriber: null,
  recorder: null,
  busy: false,
};

// ---------------------------------------------------------------------------
// Tiny DOM helpers
// ---------------------------------------------------------------------------
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];
const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  }
  for (const kid of kids) node.append(kid);
  return node;
};

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Minimal, safe markdown-ish rendering: code fences, inline code, bold, lists.
function renderMarkdown(text) {
  let html = escapeHtml(text);
  html = html.replace(/```([\s\S]*?)```/g, (_, code) => `<pre class="code">${code.replace(/^\n/, "")}</pre>`);
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/^\s*[-*]\s+(.*)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>[\s\S]*?<\/li>)/g, "<ul>$1</ul>");
  html = html.replace(/\n{2,}/g, "</p><p>").replace(/\n/g, "<br>");
  return `<p>${html}</p>`;
}

function toast(msg, isError = false) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.toggle("error", isError);
  t.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => (t.hidden = true), 4500);
}

// ---------------------------------------------------------------------------
// Context tray (screenshots + notes shared across all modes)
// ---------------------------------------------------------------------------
function renderContextTray() {
  const tray = $("#context-thumbs");
  tray.innerHTML = "";
  if (state.contextImages.length === 0) {
    tray.append(el("span", { class: "muted" }, "No context screenshots attached."));
  }
  state.contextImages.forEach((img, i) => {
    const thumb = el(
      "div",
      { class: "thumb" },
      el("img", { src: img.dataUrl, alt: "context " + (i + 1) }),
      el("button", { class: "thumb-x", title: "remove", onclick: () => {
        state.contextImages.splice(i, 1);
        renderContextTray();
      } }, "×")
    );
    tray.append(thumb);
  });
  $("#ctx-count").textContent = state.contextImages.length;
}

async function addScreenshot() {
  try {
    const img = await captureScreenshot();
    state.contextImages.push(img);
    renderContextTray();
    toast("Screenshot added to context.");
  } catch (e) {
    if (e && e.name === "NotAllowedError") return; // user cancelled the picker
    toast(e.message || "Could not capture screen.", true);
  }
}

// Ask the user to add context if none is attached. Resolves to true = proceed.
function ensureContext() {
  if (state.contextImages.length > 0 || state.notes.trim()) return Promise.resolve(true);
  return new Promise((resolve) => {
    const modal = $("#ctx-modal");
    modal.hidden = false;
    const cleanup = () => {
      modal.hidden = true;
      $("#ctx-add").onclick = null;
      $("#ctx-skip").onclick = null;
    };
    $("#ctx-add").onclick = async () => {
      cleanup();
      await addScreenshot();
      resolve(true);
    };
    $("#ctx-skip").onclick = () => {
      cleanup();
      resolve(true);
    };
  });
}

// ---------------------------------------------------------------------------
// Asking the model
// ---------------------------------------------------------------------------
function newAnswerCard(questionText) {
  const answerBody = el("div", { class: "answer-body" }, el("span", { class: "cursor" }, "▋"));
  const card = el(
    "div",
    { class: "qa-card" },
    el("div", { class: "qa-question" }, questionText || "(context only)"),
    el(
      "div",
      { class: "qa-answer" },
      answerBody,
      el("button", { class: "copy-btn", onclick: () => copyAnswer(answerBody) }, "Copy")
    )
  );
  const feed = $("#answer-feed");
  feed.prepend(card);
  return answerBody;
}

function copyAnswer(node) {
  navigator.clipboard.writeText(node.dataset.raw || node.textContent).then(
    () => toast("Answer copied."),
    () => toast("Copy failed.", true)
  );
}

async function ask({ userText, images, label }) {
  if (state.busy) {
    toast("Still answering the previous question…", true);
    return;
  }
  if (!state.apiKey) {
    toast("Add your API key in Settings first.", true);
    openSettings();
    return;
  }
  state.busy = true;
  setStatus(label || "Thinking…", true);

  const allImages = [...state.contextImages, ...(images || [])];
  const sys = state.systemPrompt + (state.notes.trim() ? `\n\nBackground notes from the user:\n${state.notes.trim()}` : "");
  const answerBody = newAnswerCard(userText);
  let raw = "";

  try {
    await streamChat(
      {
        provider: state.provider,
        apiKey: state.apiKey,
        model: state.model || PROVIDERS[state.provider].models[0].id,
        system: sys,
        userText,
        images: allImages,
        maxTokens: state.maxTokens,
      },
      (chunk) => {
        raw += chunk;
        answerBody.dataset.raw = raw;
        answerBody.innerHTML = renderMarkdown(raw) + '<span class="cursor">▋</span>';
        $("#answer-feed").scrollTop = 0;
      }
    );
    answerBody.dataset.raw = raw;
    answerBody.innerHTML = renderMarkdown(raw);
  } catch (e) {
    answerBody.innerHTML = `<p class="err">${escapeHtml(e.message || "Request failed.")}</p>`;
  } finally {
    state.busy = false;
    setStatus("Ready", false);
  }
}

function setStatus(text, busy) {
  const dot = $("#status-dot");
  $("#status-text").textContent = text;
  dot.classList.toggle("busy", !!busy);
}

// ---------------------------------------------------------------------------
// Mode: Live Copilot
// ---------------------------------------------------------------------------
function setupLiveMode() {
  const transcriptEl = $("#live-transcript");
  const btn = $("#live-toggle");

  if (!sttSupported()) {
    transcriptEl.innerHTML = '<span class="muted">Speech recognition needs Chrome or Edge.</span>';
    btn.disabled = true;
    return;
  }

  let listening = false;
  btn.onclick = () => {
    if (!listening) {
      state.transcriber = new LiveTranscriber({
        onUpdate: (finalText, interim) => {
          transcriptEl.innerHTML =
            escapeHtml(finalText) + `<span class="interim">${escapeHtml(interim)}</span>`;
          transcriptEl.scrollTop = transcriptEl.scrollHeight;
        },
        onError: (err) => toast("Mic error: " + err, true),
      });
      state.transcriber.start();
      listening = true;
      btn.textContent = "⏹ Stop listening";
      btn.classList.add("recording");
      setStatus("Listening…", true);
    } else {
      const text = state.transcriber.stop();
      listening = false;
      btn.textContent = "🎙 Start listening";
      btn.classList.remove("recording");
      setStatus("Ready", false);
      if (text) ask({ userText: text, label: "Answering…" });
    }
  };

  $("#live-ask-now").onclick = () => {
    const text = (state.transcriber && state.transcriber.finalText.trim()) || transcriptEl.textContent.trim();
    if (!text) return toast("Nothing transcribed yet.", true);
    ask({ userText: text, label: "Answering…" });
  };

  $("#live-clear").onclick = () => {
    transcriptEl.textContent = "";
    if (state.transcriber) state.transcriber.finalText = "";
  };
}

// ---------------------------------------------------------------------------
// Mode: Record -> auto-send
// ---------------------------------------------------------------------------
function setupRecordMode() {
  const btn = $("#record-btn");
  const status = $("#record-status");

  if (!sttSupported()) {
    status.innerHTML = '<span class="muted">Speech recognition needs Chrome or Edge.</span>';
    btn.disabled = true;
    return;
  }

  let recording = false;
  btn.onclick = async () => {
    if (!recording) {
      state.transcriber = new LiveTranscriber({
        onUpdate: (finalText, interim) => {
          status.innerHTML = "🔴 Recording… " + escapeHtml(finalText) +
            `<span class="interim">${escapeHtml(interim)}</span>`;
        },
        onError: (err) => toast("Mic error: " + err, true),
      });
      state.transcriber.start();
      recording = true;
      btn.classList.add("recording");
      btn.textContent = "⏹";
      setStatus("Recording…", true);
    } else {
      const text = state.transcriber.stop();
      recording = false;
      btn.classList.remove("recording");
      btn.textContent = "●";
      setStatus("Ready", false);
      status.textContent = "Sent. ";
      if (!text) return toast("Didn't catch any speech.", true);
      // "When it stops it auto-sends" — but first make sure there's context.
      await ensureContext();
      ask({ userText: text, label: "Answering recording…" });
    }
  };
}

// ---------------------------------------------------------------------------
// Mode: Describe Video
// ---------------------------------------------------------------------------
function setupVideoMode() {
  const fileInput = $("#video-file");
  const preview = $("#video-preview");
  const frameCount = $("#video-frames");

  fileInput.onchange = () => {
    const file = fileInput.files[0];
    if (!file) return;
    preview.src = URL.createObjectURL(file);
    preview.hidden = false;
  };

  $("#video-go").onclick = async () => {
    const file = fileInput.files[0];
    if (!file) return toast("Choose a video first.", true);
    const instruction = $("#video-instruction").value.trim();

    // "Context should be given to the video; if not, it asks."
    let prompt = instruction;
    if (!prompt) {
      const proceed = confirm(
        "No instructions given. I'll describe the video in detail.\n\nClick OK to continue, or Cancel to type what you want."
      );
      if (!proceed) return;
      prompt = "Describe this video in detail: what happens, who/what is shown, and any notable actions or text on screen.";
    }

    setStatus("Extracting frames…", true);
    try {
      const n = parseInt(frameCount.value, 10) || 6;
      const frames = await extractVideoFrames(file, n);
      const userText =
        `${prompt}\n\n(The following ${frames.length} images are evenly-spaced frames sampled from a single video, in chronological order.)`;
      await ask({ userText, images: frames, label: "Describing video…" });
    } catch (e) {
      toast(e.message || "Could not process video.", true);
      setStatus("Ready", false);
    }
  };
}

// ---------------------------------------------------------------------------
// Settings modal
// ---------------------------------------------------------------------------
function populateModels() {
  const sel = $("#set-model");
  sel.innerHTML = "";
  for (const m of PROVIDERS[state.provider].models) {
    sel.append(el("option", { value: m.id }, m.label));
  }
  if (state.model) sel.value = state.model;
  else state.model = PROVIDERS[state.provider].models[0].id;
}

function openSettings() {
  $("#set-provider").value = state.provider;
  populateModels();
  $("#set-key").value = state.apiKey;
  $("#set-key").placeholder = PROVIDERS[state.provider].keyHint;
  $("#set-persona").value = state.personaKey;
  $("#set-system").value = state.systemPrompt;
  $("#set-notes").value = state.notes;
  $("#set-maxtokens").value = state.maxTokens;
  $("#settings-modal").hidden = false;
}

function setupSettings() {
  $("#open-settings").onclick = openSettings;
  $("#settings-close").onclick = () => ($("#settings-modal").hidden = true);

  $("#set-provider").onchange = (e) => {
    state.provider = e.target.value;
    state.model = "";
    populateModels();
    $("#set-key").placeholder = PROVIDERS[state.provider].keyHint;
  };

  $("#set-persona").onchange = (e) => {
    state.personaKey = e.target.value;
    if (PERSONAS[e.target.value]) $("#set-system").value = PERSONAS[e.target.value].prompt;
  };

  $("#settings-save").onclick = () => {
    state.provider = $("#set-provider").value;
    state.model = $("#set-model").value;
    state.apiKey = $("#set-key").value.trim();
    state.personaKey = $("#set-persona").value;
    state.systemPrompt = $("#set-system").value.trim() || PERSONAS.general.prompt;
    state.notes = $("#set-notes").value;
    state.maxTokens = parseInt($("#set-maxtokens").value, 10) || 1024;

    LS.set("provider", state.provider);
    LS.set("model", state.model);
    LS.set("apikey", state.apiKey);
    LS.set("persona", state.personaKey);
    LS.set("systemPrompt", state.systemPrompt);
    LS.set("notes", state.notes);
    LS.set("maxTokens", String(state.maxTokens));

    $("#settings-modal").hidden = true;
    $("#persona-badge").textContent = PERSONAS[state.personaKey]?.label || "Custom";
    toast(state.apiKey ? "Settings saved." : "Saved — but no API key set yet.", !state.apiKey);
  };
}

// ---------------------------------------------------------------------------
// Tabs / boot
// ---------------------------------------------------------------------------
function setupTabs() {
  $$(".tab").forEach((tab) => {
    tab.onclick = () => {
      $$(".tab").forEach((t) => t.classList.toggle("active", t === tab));
      $$(".mode").forEach((m) => (m.hidden = m.dataset.mode !== tab.dataset.mode));
    };
  });
}

function boot() {
  setupTabs();
  setupSettings();
  setupLiveMode();
  setupRecordMode();
  setupVideoMode();
  renderContextTray();

  $("#add-screenshot").onclick = addScreenshot;
  $("#persona-badge").textContent = PERSONAS[state.personaKey]?.label || "Custom";

  if (!state.apiKey) {
    toast("Welcome — open Settings and paste your API key to begin.");
  }
}

boot();
