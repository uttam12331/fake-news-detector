// Generic, content-neutral filler lines for the simulated "other side" of a
// fake call — nothing caller-specific, just enough to sound like a live
// back-and-forth when read aloud by speech synthesis.
export const DEFAULT_LINES = [
  "Hey, can you hear me okay?",
  "Yeah, I'm doing alright, just got out of something.",
  "Oh nice, what are you up to right now?",
  "Ha, that sounds about right.",
  "Wait, say that again?",
  "Okay okay, that makes sense.",
  "I was actually just thinking about that.",
  "No way, really?",
  "Yeah I figured. Anyway, how's everything going?",
  "Honestly same here, it's been a lot lately.",
  "Let's catch up properly soon, yeah?",
  "Hold on one sec... okay, I'm back.",
  "Sorry, bad signal for a second there.",
  "Right, totally agree.",
  "Hmm, let me think about that.",
  "Anyway, I should probably get going soon.",
  "Alright, talk soon, take care!",
];

export function defaultRng() {
  return Math.random();
}

// Picks the next line index, biased away from repeating the immediately
// previous line back-to-back so a short loop doesn't feel obviously canned.
export function pickNextLineIndex(lines, lastIndex, rng = defaultRng) {
  if (!Array.isArray(lines) || lines.length === 0) return -1;
  if (lines.length === 1) return 0;
  let next = Math.floor(rng() * lines.length);
  if (next === lastIndex) {
    next = (next + 1) % lines.length;
  }
  return next;
}

// Randomized pause (ms) between spoken lines, clamped to [minMs, maxMs].
export function randomPauseMs(minMs, maxMs, rng = defaultRng) {
  const lo = Math.max(0, Math.min(minMs, maxMs));
  const hi = Math.max(minMs, maxMs);
  return Math.round(lo + rng() * (hi - lo));
}

// Builds a deterministic (given an rng) sequence of {text, pauseAfterMs} —
// pure and testable without touching window.speechSynthesis.
export function buildConversationPlan(lines, count, rng = defaultRng, pauseRange = [1200, 4000]) {
  const plan = [];
  let lastIndex = -1;
  for (let i = 0; i < count; i++) {
    const idx = pickNextLineIndex(lines, lastIndex, rng);
    if (idx === -1) break;
    lastIndex = idx;
    plan.push({
      text: lines[idx],
      pauseAfterMs: randomPauseMs(pauseRange[0], pauseRange[1], rng),
    });
  }
  return plan;
}
