// Runs generated code + its test block in a Worker: no DOM access, no
// network (the page's CSP/origin restrictions still apply), isolated from
// the main thread. The caller enforces a timeout and terminates us if we
// don't respond in time (covers infinite loops).
self.onmessage = (e) => {
  const { code, testCode } = e.data;
  const logs = [];
  let passed = 0;
  let total = 0;
  let error = null;

  const sandboxConsole = {
    log: (...args) => logs.push(args.map(String).join(" ")),
  };
  const assert = (condition, message) => {
    total++;
    if (condition) {
      passed++;
    } else {
      logs.push("FAIL: " + (message || "assertion failed"));
    }
  };

  try {
    const runUserCode = new Function("console", "assert", `${code}\n;${testCode}`);
    runUserCode(sandboxConsole, assert);
  } catch (err) {
    error = String((err && err.message) || err);
  }

  postMessage({ passed, total, logs, error });
};
