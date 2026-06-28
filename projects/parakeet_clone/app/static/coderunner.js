// Code verification: when an answer includes generated code, we don't show
// it to the user until it's been run against test cases. Only JavaScript is
// auto-executable in a browser sandbox (no network access, no external
// runtime download) — other languages are shown with a clear "not verified"
// note rather than silently skipped.

const JS_LANGS = new Set(["js", "javascript"]);
const TEST_LANGS = new Set(["test", "tests"]);

export function extractCodeBlocks(markdown) {
  const blocks = [];
  const re = /```(\w*)\n([\s\S]*?)```/g;
  let m;
  while ((m = re.exec(markdown))) {
    blocks.push({ lang: (m[1] || "").toLowerCase(), code: m[2].replace(/\n$/, ""), raw: m[0] });
  }
  return blocks;
}

export function stripCodeBlocks(markdown) {
  return markdown.replace(/```(\w*)\n([\s\S]*?)```/g, "").trim();
}

export function isJsLang(lang) {
  return JS_LANGS.has(lang);
}

export function isTestLang(lang) {
  return TEST_LANGS.has(lang);
}

// Pick the main code block and its paired test block (if any) out of all
// fenced blocks found in an answer.
export function pairCodeAndTests(blocks) {
  const test = blocks.find((b) => isTestLang(b.lang));
  const code = blocks.find((b) => !isTestLang(b.lang));
  return { code, test };
}

// Run `code` then `testCode` inside a Web Worker (no DOM/network access).
// testCode can call `assert(condition, message)` and `console.log(...)`.
// Resolves to { passed, total, logs, error }.
export function runJsTests(code, testCode, timeoutMs = 4000) {
  return new Promise((resolve) => {
    if (typeof Worker === "undefined") {
      resolve({ passed: 0, total: 0, logs: [], error: "Web Workers unavailable in this environment." });
      return;
    }
    let settled = false;
    const worker = new Worker("/static/coderunner-worker.js");
    const finish = (result) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      worker.terminate();
      resolve(result);
    };
    const timer = setTimeout(() => {
      finish({ passed: 0, total: 0, logs: [], error: `Timed out after ${timeoutMs}ms (possible infinite loop).` });
    }, timeoutMs);
    worker.onmessage = (e) => finish(e.data);
    worker.onerror = (e) => finish({ passed: 0, total: 0, logs: [], error: e.message || "Worker error" });
    worker.postMessage({ code, testCode });
  });
}

// Orchestrates: find code+tests in a raw answer, run them, report a verdict.
// `runner` is injectable for testing (defaults to the real Worker-based one).
export async function verifyCodeInAnswer(rawText, { runner = runJsTests, timeoutMs } = {}) {
  const blocks = extractCodeBlocks(rawText);
  const { code, test } = pairCodeAndTests(blocks);

  if (!code) return { hasCode: false };

  if (!isJsLang(code.lang)) {
    return { hasCode: true, verifiable: false, code, test, reason: `Auto-verification only supports JavaScript (this is "${code.lang || "unspecified"}").` };
  }
  if (!test) {
    return { hasCode: true, verifiable: false, code, test: null, reason: "No test cases were generated for this code." };
  }

  const result = await runner(code.code, test.code, timeoutMs);
  const pass = !result.error && result.total > 0 && result.passed === result.total;
  return { hasCode: true, verifiable: true, code, test, result, pass };
}
