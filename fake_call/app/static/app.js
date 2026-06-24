import { formatClock, parseDelaySeconds, initialsFor, sanitizeCallerName } from "./callsim.js";

const $ = (sel) => document.querySelector(sel);

const state = {
  countdownTimer: null,
  ringInterval: null,
  vibrateInterval: null,
  callTimer: null,
  callSeconds: 0,
  audioCtx: null,
  wakeLock: null,
};

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function showScreen(id) {
  ["setup-screen", "incoming-call", "in-call"].forEach((s) => ($("#" + s).hidden = s !== id));
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
}

function endCall() {
  clearInterval(state.callTimer);
  state.callTimer = null;
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

function boot() {
  setupForm();
  setupCosmeticButtons();
  $("#accept-call").onclick = acceptCall;
  $("#decline-call").onclick = declineCall;
  $("#end-call").onclick = endCall;
}

boot();
