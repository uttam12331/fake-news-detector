const $ = (s) => document.querySelector(s);
const HKEY = "fnd_history";
let lastText = "";

const EXAMPLES = {
  real: `WASHINGTON — The Senate on Tuesday approved a sweeping infrastructure bill that will provide funding for roads, bridges and public transit across the country. The bipartisan measure passed by a vote of 69 to 30 after weeks of negotiations between lawmakers from both parties. The President said the legislation would create millions of jobs and modernize the nation's aging infrastructure. The bill now heads to the House of Representatives, where it is expected to face additional debate before a final vote later this month, according to officials familiar with the matter. Several economists welcomed the move, saying sustained public investment could lift productivity over the next decade.`,
  fake: `SHOCKING: Scientists have CONFIRMED that drinking this one common kitchen juice every morning completely CURES cancer in just 3 days — and doctors are FURIOUS! Big Pharma has been hiding this miracle secret for decades because they don't want you to know the truth. A man from a small town says he reversed his terminal illness overnight using this trick that THEY don't want you to share. Click here before this video gets BANNED forever. Share this with everyone you love before it's too late!!!`,
};

/* ---------- tabs ---------- */
document.querySelectorAll(".tab").forEach((t) => {
  t.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((x) => x.classList.remove("active"));
    t.classList.add("active");
    $("#" + t.dataset.tab).classList.add("active");
    if (t.dataset.tab === "history") renderHistory();
  });
});

/* ---------- word counter ---------- */
const ta = $("#news");
const updateCount = () => {
  const n = (ta.value.match(/\b\w+\b/g) || []).length;
  $("#counter").textContent = n + (n === 1 ? " word" : " words");
};
ta.addEventListener("input", updateCount);

/* ---------- examples ---------- */
document.querySelectorAll(".chip").forEach((c) => {
  c.addEventListener("click", () => {
    ta.value = c.dataset.ex === "clear" ? "" : EXAMPLES[c.dataset.ex];
    updateCount();
    ta.focus();
  });
});

/* ---------- analyze ---------- */
$("#analyze").addEventListener("click", analyze);

async function analyze() {
  const text = ta.value.trim();
  if (!text) { ta.focus(); return; }
  const btn = $("#analyze");
  btn.disabled = true; btn.textContent = "Analyzing…";
  try {
    const res = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const d = await res.json();
    if (d.error) { showError(d.error); return; }
    lastText = text;
    renderResult(d);
    saveHistory(text, d);
  } catch (e) {
    showError("Could not reach the server.");
  } finally {
    btn.disabled = false; btn.textContent = "Analyze";
  }
}

function showError(msg) {
  const box = $("#result");
  box.classList.remove("hidden");
  box.innerHTML = `<div class="warn">${msg}</div>`;
}

function tagList(words, cls) {
  if (!words.length) return `<span class="tagword">—</span>`;
  return words.map((w) => `<span class="tagword">${w}</span>`).join("");
}

function renderResult(d) {
  const map = {
    FAKE: { cls: "fake", color: "var(--fake)", badge: "✕ FAKE", head: "Looks like Fake news" },
    REAL: { cls: "real", color: "var(--real)", badge: "✓ REAL", head: "Looks like Real news" },
    UNCERTAIN: { cls: "uncertain", color: "var(--warn)", badge: "? UNCERTAIN", head: "Too close to call" },
  };
  const s = map[d.verdict] || map.UNCERTAIN;
  const sub =
    d.verdict === "UNCERTAIN"
      ? `Near the 50/50 line — leans ${d.leans.toLowerCase()}, but not confidently.`
      : "";
  const box = $("#result");
  box.classList.remove("hidden");
  box.innerHTML = `
    ${d.warning ? `<div class="warn">⚠️ ${d.warning}</div>` : ""}
    <div class="verdict">
      <span class="badge ${s.cls}">${s.badge}</span>
      <div><h3>${s.head}</h3>${sub ? `<p class="sub">${sub}</p>` : ""}</div>
    </div>
    <div class="meter"><span style="width:${d.confidence}%;background:${s.color}"></span></div>
    <div class="meter-label"><span>Confidence</span><span>${d.confidence}% · (${d.fake_probability}% fake probability)</span></div>
    <div class="words">
      <div class="box"><h4 class="fakeh">↑ Pushed toward Fake</h4>${tagList(d.fake_words)}</div>
      <div class="box"><h4 class="realh">↓ Pushed toward Real</h4>${tagList(d.real_words)}</div>
    </div>
    <div class="feedback">
      <span>Teach the model — was this actually:</span>
      <button class="fb real" data-label="0">Real</button>
      <button class="fb fake" data-label="1">Fake</button>
    </div>`;
  box.querySelectorAll(".fb").forEach((b) =>
    b.addEventListener("click", () => sendFeedback(b.dataset.label))
  );
  box.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function sendFeedback(label) {
  const fb = $("#result .feedback");
  try {
    const res = await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: lastText, label }),
    });
    const d = await res.json();
    fb.innerHTML = d.ok
      ? `<span class="ok">✓ Saved as ${label === "1" ? "Fake" : "Real"}. Run <b>update_model.py</b> to fold it in.</span>`
      : `<span>${d.error || "Could not save."}</span>`;
  } catch (e) {
    fb.innerHTML = `<span>Could not reach the server.</span>`;
  }
}

/* ---------- history (localStorage) ---------- */
function saveHistory(text, d) {
  const list = JSON.parse(localStorage.getItem(HKEY) || "[]");
  list.unshift({
    snippet: text.slice(0, 90),
    verdict: d.verdict,
    confidence: d.confidence,
  });
  localStorage.setItem(HKEY, JSON.stringify(list.slice(0, 20)));
}

function renderHistory() {
  const list = JSON.parse(localStorage.getItem(HKEY) || "[]");
  const wrap = $("#history-list");
  if (!list.length) { wrap.innerHTML = `<div class="empty">No checks yet. Analyze an article to see it here.</div>`; return; }
  wrap.innerHTML = list.map((h) => {
    const cls = h.verdict === "FAKE" ? "fake" : h.verdict === "REAL" ? "real" : "uncertain";
    return `<div class="hist">
      <span class="dot ${cls}"></span>
      <span class="txt">${h.snippet || "(empty)"}…</span>
      <span class="v ${cls}">${h.verdict} ${h.confidence}%</span>
    </div>`;
  }).join("");
}

$("#clear-history").addEventListener("click", () => {
  localStorage.removeItem(HKEY);
  renderHistory();
});

updateCount();
