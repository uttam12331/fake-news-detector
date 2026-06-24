import { formatClock, parseDelaySeconds, initialsFor, sanitizeCallerName } from "./callsim.js";
import { DEFAULT_LINES, pickNextLineIndex, randomPauseMs } from "./fakevoice.js";
import { performLookup } from "./lookupClient.js";

const LOOKUP_KEY_STORAGE = "fakecall_lookup_api_key";

const $ = (sel) => document.querySelector(sel);

const state = {
  countdownTimer: null,
  ringInterval: null,
  vibrateInterval: null,
  callTimer: null,
  callSeconds: 0,
  audioCtx: null,
  wakeLock: null,
  voiceActive: false,
  voiceTimer: null,
  lastLineIndex: -1,
};

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function showScreen(id) {
  ["setup-screen", "incoming-call", "in-call"].forEach((s) => ($("#" + s).hidden = s !== id));
}

// Mock status-bar clock on the call screens — just cosmetic realism, reads
// the device's real time so it always looks plausible at a glance.
function updateStatusClocks() {
  const now = new Date();
  const h = now.getHours() % 12 || 12;
  const m = String(now.getMinutes()).padStart(2, "0");
  const text = `${h}:${m}`;
  document.querySelectorAll(".status-clock").forEach((el) => (el.textContent = text));
}

// ---------------------------------------------------------------------------
// Ringtone + vibration — synthesised with WebAudio so no audio file needs to
// ship with the app. Classic two-tone "ring ring … pause" pattern.
// ---------------------------------------------------------------------------
function beep(ctx, freq, startAt, duration) {
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.frequency.value = freq;
  osc.type = "sine";
  gain.gain.setValueAtTime(0, startAt);
  gain.gain.linearRampToValueAtTime(0.25, startAt + 0.02);
  gain.gain.linearRampToValueAtTime(0, startAt + duration);
  osc.connect(gain);
  gain.connect(ctx.destination);
  osc.start(startAt);
  osc.stop(startAt + duration + 0.02);
}

function playRingCycle(ctx) {
  const now = ctx.currentTime;
  // Two short tones, twice, like a classic ring, then silence until the
  // interval below schedules the next cycle.
  [0, 0.4].forEach((offset) => {
    beep(ctx, 480, now + offset, 0.35);
    beep(ctx, 440, now + offset, 0.35);
  });
}

function startRinging() {
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return;
  state.audioCtx = new Ctx();
  playRingCycle(state.audioCtx);
  state.ringInterval = setInterval(() => playRingCycle(state.audioCtx), 2000);

  if (navigator.vibrate) {
    const pattern = [500, 200, 500, 1300];
    navigator.vibrate(pattern);
    state.vibrateInterval = setInterval(() => navigator.vibrate(pattern), 2500);
  }
}

function stopRinging() {
  clearInterval(state.ringInterval);
  state.ringInterval = null;
  clearInterval(state.vibrateInterval);
  state.vibrateInterval = null;
  if (navigator.vibrate) navigator.vibrate(0);
  if (state.audioCtx) {
    state.audioCtx.close().catch(() => {});
    state.audioCtx = null;
  }
}

async function acquireWakeLock() {
  try {
    if (navigator.wakeLock) state.wakeLock = await navigator.wakeLock.request("screen");
  } catch (_) {
    // Not supported, or denied — the fake call still works without it.
  }
}

function releaseWakeLock() {
  if (state.wakeLock) {
    state.wakeLock.release().catch(() => {});
    state.wakeLock = null;
  }
}

// ---------------------------------------------------------------------------
// Fake voice — speaks the "other side" of the call with the Web Speech
// Synthesis API so accepting feels like an actual two-way conversation.
// ---------------------------------------------------------------------------
function speakNextLine() {
  if (!state.voiceActive || !window.speechSynthesis) return;
  const idx = pickNextLineIndex(DEFAULT_LINES, state.lastLineIndex);
  state.lastLineIndex = idx;
  const utter = new SpeechSynthesisUtterance(DEFAULT_LINES[idx]);
  utter.rate = 1;
  utter.pitch = 1;
  utter.onend = () => {
    if (!state.voiceActive) return;
    state.voiceTimer = setTimeout(speakNextLine, randomPauseMs(1200, 4000));
  };
  // If speech synthesis fails to fire onend (some mobile WebViews), still
  // recover instead of going silent for the rest of the call.
  utter.onerror = utter.onend;
  window.speechSynthesis.speak(utter);
}

function startFakeVoice() {
  if (!window.speechSynthesis) return;
  state.voiceActive = true;
  state.lastLineIndex = -1;
  state.voiceTimer = setTimeout(speakNextLine, 700);
}

function stopFakeVoice() {
  state.voiceActive = false;
  clearTimeout(state.voiceTimer);
  state.voiceTimer = null;
  if (window.speechSynthesis) window.speechSynthesis.cancel();
}

// ---------------------------------------------------------------------------
// Call flow
// ---------------------------------------------------------------------------
function triggerIncomingCall(name, subtitle) {
  $("#call-avatar").textContent = initialsFor(name);
  $("#call-name").textContent = name;
  $("#call-subtitle-incoming").textContent = subtitle || "Mobile";
  showScreen("incoming-call");
  acquireWakeLock();
  startRinging();
}

function acceptCall() {
  stopRinging();
  const name = $("#call-name").textContent;
  $("#in-call-avatar").textContent = initialsFor(name);
  $("#in-call-name").textContent = name;
  state.callSeconds = 0;
  $("#in-call-timer").textContent = formatClock(0);
  showScreen("in-call");
  state.callTimer = setInterval(() => {
    state.callSeconds++;
    $("#in-call-timer").textContent = formatClock(state.callSeconds);
  }, 1000);
  if ($("#fake-voice-toggle").checked) startFakeVoice();
}

function endCall() {
  clearInterval(state.callTimer);
  state.callTimer = null;
  stopFakeVoice();
  releaseWakeLock();
  resetToSetup();
}

function declineCall() {
  stopRinging();
  releaseWakeLock();
  resetToSetup();
}

function resetToSetup() {
  showScreen("setup-screen");
  $("#cancel-row").hidden = true;
  $("#start-call-btn").disabled = false;
}

// ---------------------------------------------------------------------------
// Setup screen
// ---------------------------------------------------------------------------
function setupForm() {
  const delaySelect = $("#call-delay");
  const customWrap = $("#custom-delay-wrap");
  delaySelect.onchange = () => {
    customWrap.hidden = delaySelect.value !== "custom";
  };

  $("#start-call-btn").onclick = () => {
    const name = sanitizeCallerName($("#caller-name").value);
    const subtitle = ($("#caller-subtitle").value || "Mobile").trim() || "Mobile";
    const delaySeconds = parseDelaySeconds(delaySelect.value, $("#custom-delay").value);

    if (delaySeconds === 0) {
      triggerIncomingCall(name, subtitle);
      return;
    }

    $("#start-call-btn").disabled = true;
    const cancelRow = $("#cancel-row");
    cancelRow.hidden = false;
    let remaining = delaySeconds;
    $("#cancel-countdown").textContent = remaining;
    state.countdownTimer = setInterval(() => {
      remaining--;
      $("#cancel-countdown").textContent = remaining;
      if (remaining <= 0) {
        clearInterval(state.countdownTimer);
        state.countdownTimer = null;
        cancelRow.hidden = true;
        $("#start-call-btn").disabled = false;
        triggerIncomingCall(name, subtitle);
      }
    }, 1000);
  };

  $("#cancel-scheduled").onclick = () => {
    clearInterval(state.countdownTimer);
    state.countdownTimer = null;
    $("#cancel-row").hidden = true;
    $("#start-call-btn").disabled = false;
  };
}

// Cosmetic-only in-call buttons (mute/speaker/keypad): this is a fake call,
// there's no real audio stream to mute, so they just toggle a pressed look.
function setupCosmeticButtons() {
  document.querySelectorAll(".incall-toggle").forEach((btn) => {
    btn.onclick = () => btn.classList.toggle("active");
  });
}

// ---------------------------------------------------------------------------
// Setup screen tabs (fake call vs. number lookup)
// ---------------------------------------------------------------------------
function setupTabs() {
  const buttons = document.querySelectorAll(".tab-btn");
  buttons.forEach((btn) => {
    btn.onclick = () => {
      buttons.forEach((b) => b.classList.toggle("active", b === btn));
      $("#call-tab").hidden = btn.dataset.tab !== "call";
      $("#lookup-tab").hidden = btn.dataset.tab !== "lookup";
    };
  });
}

// ---------------------------------------------------------------------------
// Number lookup — carrier/line-type/location only, never a caller's name
// (see the disclosure text in the lookup tab for why).
// ---------------------------------------------------------------------------
function renderLookupResult(result) {
  const box = $("#lookup-result");
  box.hidden = false;

  if (result.error) {
    box.classList.add("error");
    box.innerHTML = `<div class="row"><span class="v">${escapeHtml(result.error)}</span></div>`;
    return;
  }

  box.classList.remove("error");
  const rows = [
    ["Valid", result.valid ? "Yes" : "No"],
    ["Number", result.number],
    ["Country", result.countryName],
    ["Location", result.location],
    ["Carrier", result.carrier],
    ["Line type", result.lineType],
  ].filter(([, v]) => v);

  box.innerHTML = rows
    .map(([k, v]) => `<div class="row"><span class="k">${escapeHtml(k)}</span><span class="v">${escapeHtml(String(v))}</span></div>`)
    .join("");
}

function setupLookupTab() {
  const keyInput = $("#lookup-api-key");
  keyInput.value = localStorage.getItem(LOOKUP_KEY_STORAGE) || "";
  keyInput.onchange = () => localStorage.setItem(LOOKUP_KEY_STORAGE, keyInput.value.trim());

  $("#lookup-btn").onclick = async () => {
    const number = $("#lookup-number").value.trim();
    const apiKey = keyInput.value.trim();
    const btn = $("#lookup-btn");

    if (!number) {
      renderLookupResult({ error: "Enter a phone number first." });
      return;
    }
    if (!apiKey) {
      renderLookupResult({ error: "Paste an API key in Settings below first." });
      return;
    }

    btn.disabled = true;
    btn.textContent = "Checking…";
    try {
      const result = await performLookup(number, apiKey);
      renderLookupResult(result);
    } catch (_) {
      renderLookupResult({ error: "Could not reach the lookup provider." });
    } finally {
      btn.disabled = false;
      btn.textContent = "🔎 Check number";
    }
  };
}

function boot() {
  setupForm();
  setupCosmeticButtons();
  setupTabs();
  setupLookupTab();
  $("#accept-call").onclick = acceptCall;
  $("#decline-call").onclick = declineCall;
  $("#end-call").onclick = endCall;
  updateStatusClocks();
  setInterval(updateStatusClocks, 15000);
}

boot();
