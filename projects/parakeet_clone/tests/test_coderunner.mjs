// Run with: node tests/test_coderunner.mjs
import assert from "node:assert";
import {
  extractCodeBlocks,
  stripCodeBlocks,
  isJsLang,
  isTestLang,
  pairCodeAndTests,
  verifyCodeInAnswer,
} from "../app/static/coderunner.js";

let passed = 0;
async function test(name, fn) {
  try {
    await fn();
    passed++;
    console.log("ok -", name);
  } catch (e) {
    console.error("FAIL -", name);
    console.error(e);
    process.exitCode = 1;
  }
}

const ANSWER_WITH_TESTS = [
  "Here's a function that adds two numbers:",
  "",
  "```js",
  "function add(a, b) { return a + b; }",
  "```",
  "",
  "And here are some checks:",
  "",
  "```test",
  "assert(add(2, 3) === 5, 'add(2,3) should be 5');",
  "assert(add(-1, 1) === 0, 'add(-1,1) should be 0');",
  "```",
].join("\n");

const ANSWER_PYTHON = ["```python", "def add(a, b):\n    return a + b", "```"].join("\n");

const ANSWER_NO_CODE = "Just a plain explanation with **bold** text, no code here.";

await test("extractCodeBlocks finds language and code, trims trailing newline", () => {
  const blocks = extractCodeBlocks(ANSWER_WITH_TESTS);
  assert.equal(blocks.length, 2);
  assert.equal(blocks[0].lang, "js");
  assert.equal(blocks[0].code, "function add(a, b) { return a + b; }");
  assert.equal(blocks[1].lang, "test");
});

await test("stripCodeBlocks removes fences, keeps prose", () => {
  const stripped = stripCodeBlocks(ANSWER_WITH_TESTS);
  assert.ok(stripped.includes("Here's a function"));
  assert.ok(!stripped.includes("function add"));
});

await test("isJsLang / isTestLang classify correctly", () => {
  assert.ok(isJsLang("js"));
  assert.ok(isJsLang("javascript"));
  assert.ok(!isJsLang("python"));
  assert.ok(isTestLang("test"));
  assert.ok(isTestLang("tests"));
  assert.ok(!isTestLang("js"));
});

await test("pairCodeAndTests picks the non-test block as code", () => {
  const blocks = extractCodeBlocks(ANSWER_WITH_TESTS);
  const { code, test } = pairCodeAndTests(blocks);
  assert.equal(code.lang, "js");
  assert.equal(test.lang, "test");
});

await test("verifyCodeInAnswer: no code -> hasCode false", async () => {
  const v = await verifyCodeInAnswer(ANSWER_NO_CODE);
  assert.equal(v.hasCode, false);
});

await test("verifyCodeInAnswer: non-JS code -> not verifiable, explains why", async () => {
  const v = await verifyCodeInAnswer(ANSWER_PYTHON);
  assert.equal(v.hasCode, true);
  assert.equal(v.verifiable, false);
  assert.match(v.reason, /JavaScript/);
});

await test("verifyCodeInAnswer: JS with no test block -> not verifiable", async () => {
  const v = await verifyCodeInAnswer("```js\nfunction f(){return 1;}\n```");
  assert.equal(v.hasCode, true);
  assert.equal(v.verifiable, false);
  assert.match(v.reason, /No test cases/);
});

await test("verifyCodeInAnswer: JS + passing tests -> pass true, uses injected runner", async () => {
  const fakeRunner = async (code, testCode) => {
    assert.ok(code.includes("function add"));
    assert.ok(testCode.includes("assert("));
    return { passed: 2, total: 2, logs: [], error: null };
  };
  const v = await verifyCodeInAnswer(ANSWER_WITH_TESTS, { runner: fakeRunner });
  assert.equal(v.verifiable, true);
  assert.equal(v.pass, true);
  assert.equal(v.result.passed, 2);
});

await test("verifyCodeInAnswer: JS + failing tests -> pass false", async () => {
  const fakeRunner = async () => ({ passed: 1, total: 2, logs: ["FAIL: add(-1,1) should be 0"], error: null });
  const v = await verifyCodeInAnswer(ANSWER_WITH_TESTS, { runner: fakeRunner });
  assert.equal(v.verifiable, true);
  assert.equal(v.pass, false);
});

await test("verifyCodeInAnswer: runner throws/returns error -> pass false", async () => {
  const fakeRunner = async () => ({ passed: 0, total: 0, logs: [], error: "ReferenceError: x is not defined" });
  const v = await verifyCodeInAnswer(ANSWER_WITH_TESTS, { runner: fakeRunner });
  assert.equal(v.pass, false);
  assert.match(v.result.error, /ReferenceError/);
});

console.log(`\n${passed} checks passed.`);
