# How It Works — Uttam Limbani Fake News Detector

A plain-English explanation of the whole system, end to end. No prior ML knowledge needed.

---

## 1. The one-sentence summary

The app does **not** understand news or check whether a story is true. It learned, from
~20,800 articles that humans already labelled "real" or "fake," **which words and phrases
tend to appear in each kind**, and then scores your text on those patterns.

> It is a **writing-style detector**, not a truth detector.

---

## 2. What happens when you click "Analyze"

```
Your text
   │
   ▼
[1] CLEAN & VECTORIZE   →  turn words into ~50,000 numbers (TF-IDF)
   │
   ▼
[2] SCORE              →  multiply each number by a learned "fakeness weight" and add up
   │                      → squash into a 0–100% probability of fake (logistic/sigmoid)
   ▼
[3] DECIDE & EXPLAIN   →  REAL / FAKE / UNCERTAIN  +  the words that moved the needle
```

### Stage 1 — Words → numbers (TF-IDF)

A model can only do maths, not read. So the text is converted into a long list of numbers,
one slot per word/phrase the model knows. Each number is a **TF-IDF** score:

- **TF (term frequency)** — how often the word appears in *your* text.
- **IDF (inverse document frequency)** — how *rare/distinctive* the word is across all news.
  Common words ("the", "and") get crushed to near-zero; distinctive ones ("miracle",
  "Reuters", "Senate") get high weights.

Code: `VECTORIZER.transform([text])` in [app.py](app.py).

### Stage 2 — Score it (Logistic Regression)

During training, the model learned a **weight** for each of the ~50,000 words — a number
saying "how fake-ish is this word":

- Positive weight → pushes toward **FAKE** (e.g. *shocking, click, secret, pharma*)
- Negative weight → pushes toward **REAL** (e.g. *Reuters, officials, Tuesday, senate*)

Scoring is just: **(each word's TF-IDF) × (its weight), summed up**, then passed through the
logistic (sigmoid) function to get a probability between 0% and 100%.

```
score = tfidf["shocking"]·w["shocking"] + tfidf["click"]·w["click"]
      + tfidf["reuters"]·w["reuters"]  (negative, pulls back toward real) + … 50,000 terms
→ sigmoid → e.g. 99.4% fake
```

Code: `MODEL.predict_proba(vec)` in [app.py](app.py).

### Stage 3 — Decide and explain

- **≥ 60% one way** → `REAL` or `FAKE`.
- **40–60% (near the boundary)** → `UNCERTAIN` — so the app never fakes confidence.
- **The "why" words** are literally the terms with the largest `tfidf × weight` contribution.

---

## 3. Where the "intelligence" lives

All the knowledge is in those ~50,000 weights. They were set **once**, during training
([train_model.py](train_model.py)): the model was shown 16,640 pre-labelled articles and
adjusted its weights until its guesses matched the labels, reaching **97.8% accuracy** on
4,160 articles it had never seen. Those frozen weights are saved in `model/pipeline.pkl`.
The running app just loads them and does the multiply-and-add.

---

## 4. The files

| File | What it is |
|------|------------|
| `app.py` | The Flask web server + the `analyze()` function (the 3 stages above). |
| `train_model.py` | Trains the model from scratch on the Kaggle dataset. |
| `update_model.py` | **Keeps it current** — retrains including recent / user-supplied data. |
| `recent_2026.csv` | Recent (2026) labelled examples folded into the model. |
| `feedback.csv` | Examples you label in the app ("Was this right?") — used by `update_model.py`. |
| `model/pipeline.pkl` | The saved vectorizer + trained model (the "brain"). |
| `templates/index.html` | The web page. |
| `static/style.css`, `static/app.js` | Look and behaviour of the page. |
| `run.bat` | One-click launcher. |

---

## 5. "How can it know 2026 data?" — the honest answer

A model can only know what it was trained on. The original brain was trained on a **2017**
dataset, so it had never seen 2026 names, events, or vocabulary. There is no magic that lets
it "know" 2026 on its own — **the only real way is to retrain it with recent, labelled data.**

So this project makes the model **continuously updatable** in two ways:

1. **`recent_2026.csv`** — a starter set of current (2026) real and fake examples that are
   folded into the model by `update_model.py`. This teaches it today's vocabulary and topics.
2. **In-app feedback loop** — after each result you can press **"Mark Real"** / **"Mark Fake."**
   That example is appended to `feedback.csv`. Running `update_model.py` again retrains the
   model on the original data **plus** everything in `recent_2026.csv` and `feedback.csv`, so
   it keeps getting more current the more you (or a scheduled job) feed it.

### To refresh the brain yourself

```powershell
cd "$env:USERPROFILE\Downloads\FakeNews-Detector-Pro"
.\venv\Scripts\python.exe update_model.py     # retrains and overwrites model/pipeline.pkl
```

Then restart the app. To make it truly current long-term, add more recent rows to
`recent_2026.csv` (or keep labelling in the app) and re-run the command — ideally on a
schedule (e.g. monthly).

---

## 6. The limitation that no amount of data fixes

Because it scores *style*, not *facts*:

- A scammer writing in calm, "Reuters-style" prose can score **REAL**.
- A true story written in breathless ALL-CAPS can score **FAKE**.

Use it as a **signal and a learning tool**, not as a final verdict on whether something is true.
