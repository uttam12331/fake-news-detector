// Run with: node tests/test_fakevoice.mjs
import assert from "node:assert";
import {
  DEFAULT_LINES,
  pickNextLineIndex,
  randomPauseMs,
  buildConversationPlan,
} from "../app/static/fakevoice.js";

let passed = 0;
function test(name, fn) {
  try {
    fn();
    passed++;
    console.log("ok -", name);
  } catch (e) {
    console.error("FAIL -", name);
    console.error(e);
    process.exitCode = 1;
  }
}

function seededRng(seq) {
  let i = 0;
  return () => seq[i++ % seq.length];
}

test("pickNextLineIndex avoids immediate repeats", () => {
  const lines = ["a", "b", "c"];
  // rng() * 3 -> 0, then again 0 (would repeat index 0) -> should advance to 1
  const rng = seededRng([0, 0]);
  const first = pickNextLineIndex(lines, -1, rng);
  assert.equal(first, 0);
  const second = pickNextLineIndex(lines, first, rng);
  assert.equal(second, 1);
});

test("pickNextLineIndex handles empty/single-element lists", () => {
  assert.equal(pickNextLineIndex([], -1, () => 0), -1);
  assert.equal(pickNextLineIndex(["only"], 0, () => 0.9), 0);
});

test("randomPauseMs stays within [min, max] and handles swapped args", () => {
  for (const r of [0, 0.5, 0.999]) {
    const v = randomPauseMs(1000, 3000, () => r);
    assert.ok(v >= 1000 && v <= 3000, `${v} out of range`);
  }
  const swapped = randomPauseMs(3000, 1000, () => 0.5);
  assert.ok(swapped >= 1000 && swapped <= 3000);
});

test("buildConversationPlan produces requested count with text + pause", () => {
  const rng = seededRng([0.1, 0.2, 0.4, 0.6, 0.8, 0.9]);
  const plan = buildConversationPlan(DEFAULT_LINES, 3, rng);
  assert.equal(plan.length, 3);
  plan.forEach((step) => {
    assert.equal(typeof step.text, "string");
    assert.ok(DEFAULT_LINES.includes(step.text));
    assert.ok(step.pauseAfterMs >= 0);
  });
});

test("buildConversationPlan is deterministic for a given rng sequence", () => {
  const seq = [0.05, 0.15, 0.25, 0.35, 0.45, 0.55];
  const planA = buildConversationPlan(DEFAULT_LINES, 3, seededRng(seq));
  const planB = buildConversationPlan(DEFAULT_LINES, 3, seededRng(seq));
  assert.deepEqual(planA, planB);
});

console.log(`\n${passed} checks passed.`);
