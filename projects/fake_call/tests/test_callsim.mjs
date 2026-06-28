// Run with: node tests/test_callsim.mjs
import assert from "node:assert";
import { formatClock, parseDelaySeconds, initialsFor, sanitizeCallerName } from "../app/static/callsim.js";

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

test("formatClock formats mm:ss, pads seconds", () => {
  assert.equal(formatClock(0), "0:00");
  assert.equal(formatClock(5), "0:05");
  assert.equal(formatClock(65), "1:05");
  assert.equal(formatClock(600), "10:00");
  assert.equal(formatClock(-3), "0:00");
});

test("parseDelaySeconds handles presets and custom", () => {
  assert.equal(parseDelaySeconds("0"), 0);
  assert.equal(parseDelaySeconds("10"), 10);
  assert.equal(parseDelaySeconds("60"), 60);
  assert.equal(parseDelaySeconds("custom", "45"), 45);
  assert.equal(parseDelaySeconds("custom", "abc"), 0);
  assert.equal(parseDelaySeconds("custom", "-5"), 0);
});

test("initialsFor builds up to 2 letters from name", () => {
  assert.equal(initialsFor("Mom"), "M");
  assert.equal(initialsFor("John Smith"), "JS");
  assert.equal(initialsFor("  "), "?");
  assert.equal(initialsFor(""), "?");
});

test("sanitizeCallerName trims, caps length, falls back", () => {
  assert.equal(sanitizeCallerName("  Boss  "), "Boss");
  assert.equal(sanitizeCallerName(""), "Unknown");
  assert.equal(sanitizeCallerName("a".repeat(100)).length, 40);
});

console.log(`\n${passed} checks passed.`);
