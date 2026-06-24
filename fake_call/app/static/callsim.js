// Pure scheduling/formatting helpers for the fake-call simulator — kept
// dependency-free (no DOM/WebAudio) so they're testable under plain Node.

export function formatClock(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds));
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${String(sec).padStart(2, "0")}`;
}

// `spec` is one of the preset delay values ("0", "5", "10", "30", "60") or
// "custom", in which case `customValue` (seconds, as typed by the user) is used.
export function parseDelaySeconds(spec, customValue) {
  const raw = spec === "custom" ? customValue : spec;
  const n = parseInt(raw, 10);
  return Number.isFinite(n) && n >= 0 ? n : 0;
}

export function initialsFor(name) {
  const trimmed = (name || "").trim();
  if (!trimmed) return "?";
  const parts = trimmed.split(/\s+/).filter(Boolean);
  const chars = parts.slice(0, 2).map((p) => p[0].toUpperCase());
  return chars.join("") || "?";
}

export function sanitizeCallerName(name, fallback = "Unknown") {
  const trimmed = (name || "").trim();
  return trimmed.length > 0 ? trimmed.slice(0, 40) : fallback;
}
