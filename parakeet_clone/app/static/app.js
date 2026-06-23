import { PROVIDERS, streamChat } from "./providers.js";
import { LiveTranscriber, isSupported as sttSupported } from "./transcribe.js";
import { captureScreenshot, extractVideoFrames, AudioRecorder } from "./capture.js";
import { stripCodeBlocks, extractCodeBlocks, pairCodeAndTests, verifyCodeInAnswer } from "./coderunner.js";
import * as History from "./history.js";

// Appended to every system prompt so the model knows the code+test contract:
// code is never shown to the user until it's been run, so it must hand us
// something runnable to test against.
const CODE_TEST_INSTRUCTION =
  "\n\nWhen your answer includes a code solution written in JavaScript, follow it with a " +
  "second fenced block labeled ```test containing JavaScript assertions that exercise the code " +
  'using assert(condition, message) — at least 2 cases, e.g. assert(add(2, 3) === 5, "2+3 should be 5"). ' +
  "The test block must call the exact function/variable names defined in the code block. " +
  "For any other programming language, just give the code without a test block.";

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
  meetingId: History.getOrCreateCurrentMeeting().id,
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

function buildSystemPrompt() {
  let sys = state.systemPrompt + CODE_TEST_INSTRUCTION;
  if (state.notes.trim()) sys += `\n\nBackground notes from the user:\n${state.notes.trim()}`;
  return sys;
}

// Renders prose + (if present) a distinct, badged code section. Used for both
// the live answer feed and the meeting-history view — `meta` either carries a
// fresh verification result (live) or the smaller persisted summary (history).
function renderAnswerBlock(container, rawText, meta) {
  container.dataset.raw = rawText;
  if (!meta || !meta.hasCode) {
    container.innerHTML = renderMarkdown(rawText);
    return;
  }

  const blocks = extractCodeBlocks(rawText);
  const { code, test } = pairCodeAndTests(blocks);
  const prose = stripCodeBlocks(rawText);
  const pass = meta.pass ?? meta.verified;
  const badge = !meta.verifiable
    ? { cls: "info", text: "Not verified" }
    : pass
    ? { cls: "pass", text: "✓ Tests passed" }
    : { cls: "fail", text: "✗ Tests failed" };

  let body = `<pre class="code">${escapeHtml(code ? code.code : "")}</pre>`;
  if (meta.verifiable && test) {
    body += `<details class="test-details"><summary>Test cases</summary><pre class="code">${escapeHtml(test.code)}</pre></details>`;
  }
  const note = meta.reason || meta.resultSummary;
  if (note) body += `<p class="code-sub-label muted">${escapeHtml(note)}</p>`;
  if (meta.result) {
    if (meta.result.error) body += `<p class="code-error">${escapeHtml(meta.result.error)}</p>`;
    if (meta.result.logs && meta.result.logs.length) body += `<pre class="code logs">${escapeHtml(meta.result.logs.join("\n"))}</pre>`;
  }

  const lang = (code && code.lang) || "code";
  container.innerHTML =
    renderMarkdown(prose) +
    `<div class="code-section"><div class="code-head"><span class="code-lang">${escapeHtml(lang)}</span>` +
    `<span class="code-badge ${badge.cls}">${badge.text}</span></div>${body}</div>`;
}

function summarizeVerification(v) {
  if (!v.hasCode) return null;
  if (!v.verifiable) return v.reason;
  if (v.pass) return `Tests passed (${v.result.passed}/${v.result.total}).`;
  return `Tests failed (${v.result.passed}/${v.result.total}).`;
}

async function ask({ userText, images, label, mode = "qa", onlyImages = false }) {
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

  const allImages = onlyImages ? images || [] : [...state.contextImages, ...(images || [])];
  const sys = buildSystemPrompt();
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
        // Hide everything from the first code fence onward while streaming —
        // code is never shown until it's been run and tested.
        const fenceIdx = raw.indexOf("```");
        const hasFence = fenceIdx !== -1;
        answerBody.dataset.raw = raw;
        const prose = hasFence ? raw.slice(0, fenceIdx) : raw;
        let html = renderMarkdown(prose) + '<span class="cursor">▋</span>';
        if (hasFence) {
          html += `<div class="code-pending muted">⏳ Writing code — it'll be tested before it's shown…</div>`;
        }
        answerBody.innerHTML = html;
        $("#answer-feed").scrollTop = 0;
      }
    );

    let verification = await verifyCodeInAnswer(raw);

    // Code that fails its own tests gets exactly one fix attempt before we
    // give up and show the (marked failing) result anyway.
    if (verification.verifiable && !verification.pass) {
      setStatus("Tests failed — asking the model to fix it…", true);
      const r = verification.result;
      const failDetail = r.error
        ? `Error: ${r.error}`
        : `${r.passed}/${r.total} tests passed.${r.logs.length ? " Logs: " + r.logs.join("; ") : ""}`;
      let fixed = "";
      try {
        await streamChat(
          {
            provider: state.provider,
            apiKey: state.apiKey,
            model: state.model || PROVIDERS[state.provider].models[0].id,
            system: sys,
            userText:
              `Your previous code failed its tests. ${failDetail}\n\n` +
              "Fix the code and reply with the corrected code block followed by an updated test block.",
            history: [
              { role: "user", text: userText },
              { role: "assistant", text: raw },
            ],
            images: [],
            maxTokens: state.maxTokens,
          },
          (chunk) => (fixed += chunk)
        );
      } catch (_) {
        // Keep the original (failing) answer if the fix attempt itself errors.
      }
      if (fixed.trim()) {
        raw = fixed;
        verification = await verifyCodeInAnswer(raw);
      }
    }

    renderAnswerBlock(answerBody, raw, verification);

    History.addEntry(state.meetingId, {
      mode,
      question: userText || "(context only)",
      answerRaw: raw,
      screenshotCount: allImages.length,
      hasCode: !!verification.hasCode,
      verifiable: !!verification.verifiable,
      verified: verification.verifiable ? !!verification.pass : null,
      resultSummary: summarizeVerification(verification),
    });
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
      if (text) ask({ userText: text, label: "Answering…", mode: "live" });
    }
  };

  $("#live-ask-now").onclick = () => {
    const text = (state.transcriber && state.transcriber.finalText.trim()) || transcriptEl.textContent.trim();
    if (!text) return toast("Nothing transcribed yet.", true);
    ask({ userText: text, label: "Answering…", mode: "live" });
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
      ask({ userText: text, label: "Answering recording…", mode: "record" });
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
      await ask({ userText, images: frames, label: "Describing video…", mode: "video" });
    } catch (e) {
      toast(e.message || "Could not process video.", true);
      setStatus("Ready", false);
    }
  };
}

// ---------------------------------------------------------------------------
// Answer from Screen — one fresh screenshot, answered on its own (no
// accumulated context tray screenshots mixed in).
// ---------------------------------------------------------------------------
function setupScreenAnswer() {
  $("#answer-screen-btn").onclick = async () => {
    setStatus("Capturing screen…", true);
    try {
      const shot = await captureScreenshot();
      await ask({
        userText: "Look only at this screenshot. Answer the question, solve the problem, or describe what's shown — whatever is most useful.",
        images: [shot],
        onlyImages: true,
        mode: "screen",
        label: "Answering from screen…",
      });
    } catch (e) {
      setStatus("Ready", false);
      if (e && e.name === "NotAllowedError") return; // user cancelled the picker
      toast(e.message || "Could not capture screen.", true);
    }
  };
}

// ---------------------------------------------------------------------------
// Meeting history
// ---------------------------------------------------------------------------
function refreshMeetingTitle() {
  const m = History.getMeeting(state.meetingId);
  $("#meeting-title").textContent = m ? m.title : "";
}

function setupMeetingControls() {
  $("#new-meeting").onclick = () => {
    const m = History.startNewMeeting();
    state.meetingId = m.id;
    refreshMeetingTitle();
    $("#answer-feed").innerHTML = "";
    toast("Started a new meeting.");
  };

  $("#meeting-title").ondblclick = () => {
    const m = History.getMeeting(state.meetingId);
    const newTitle = prompt("Rename meeting", m ? m.title : "");
    if (newTitle) {
      History.renameMeeting(state.meetingId, newTitle);
      refreshMeetingTitle();
    }
  };
}

function renderHistoryView() {
  const list = $("#history-list");
  list.innerHTML = "";
  const meetings = History.listMeetings();
  if (meetings.length === 0) {
    list.append(el("p", { class: "muted" }, "No meetings yet — ask something to start one."));
    return;
  }

  meetings.forEach((m) => {
    const body = el("div", { class: "meeting-body" });
    m.entries
      .slice()
      .reverse()
      .forEach((entry) => {
        const answerEl = el("div", { class: "answer-body" });
        renderAnswerBlock(answerEl, entry.answerRaw, {
          hasCode: entry.hasCode,
          verifiable: entry.verifiable,
          verified: entry.verified,
          resultSummary: entry.resultSummary,
        });
        body.append(
          el(
            "div",
            { class: "history-entry" },
            el(
              "div",
              { class: "qa-question" },
              entry.question + (entry.screenshotCount ? ` · 📸 ${entry.screenshotCount}` : "")
            ),
            el("div", { class: "qa-answer" }, answerEl)
          )
        );
      });

    const card = el("div", { class: "meeting-card" });
    const head = el(
      "div",
      { class: "meeting-head", onclick: () => card.classList.toggle("open") },
      el("strong", {}, m.title),
      el("span", { class: "muted" }, ` · ${m.entries.length} exchange${m.entries.length === 1 ? "" : "s"}`),
      el(
        "button",
        {
          class: "ghost-btn small danger",
          onclick: (e) => {
            e.stopPropagation();
            if (confirm("Delete this meeting? This can't be undone.")) {
              History.deleteMeeting(m.id);
              renderHistoryView();
            }
          },
        },
        "Delete"
      )
    );
    card.append(head, body);
    list.append(card);
  });
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
      const isHistory = tab.dataset.mode === "history";
      $$(".tab").forEach((t) => t.classList.toggle("active", t === tab));
      $$(".mode").forEach((m) => (m.hidden = m.dataset.mode !== tab.dataset.mode));
      $(".layout").hidden = isHistory;
      $("#history-view").hidden = !isHistory;
      if (isHistory) renderHistoryView();
    };
  });
}

function boot() {
  setupTabs();
  setupSettings();
  setupLiveMode();
  setupRecordMode();
  setupVideoMode();
  setupScreenAnswer();
  setupMeetingControls();
  renderContextTray();
  refreshMeetingTitle();

  $("#add-screenshot").onclick = addScreenshot;
  $("#persona-badge").textContent = PERSONAS[state.personaKey]?.label || "Custom";

  if (!state.apiKey) {
    toast("Welcome — open Settings and paste your API key to begin.");
  }
}

boot();
