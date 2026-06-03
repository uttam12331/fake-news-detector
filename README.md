# Fake News Detector

A small web app that reads a news article and tells you whether it looks **real**, **fake**, or **too close to call** — along with a confidence score and the actual words that pushed it one way or the other.

Built by **Uttam Limbani**.

![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![Flask](https://img.shields.io/badge/flask-web%20app-black) ![Model](https://img.shields.io/badge/model-TF--IDF%20%2B%20Logistic%20Regression-green)

---

## Why I built this

I came across an old fake-news-detection project on GitHub and tried to run it. It didn't really work for me — the saved model had been trained on a years-old version of scikit-learn, so loading it threw warnings about the results being unreliable, and the web page asked you to type a "headline" while the model had actually been trained on full article bodies. So pretty much anything short you typed came back as "Fake."

Instead of patching it, I rebuilt the whole thing from scratch:

- retrained the model on the current libraries so there are no version warnings
- trained it on the title **and** the body so short text doesn't break it
- swapped in a model that gives a real confidence percentage and can explain itself
- redid the UI
- and — the part I cared about most — made the model **updatable**, with some 2026 data folded in, since the original only knew news up to around 2017.

It's a learning / portfolio project. It is **not** a tool you should trust to tell you what's true (more on that at the bottom).

---

## What it does

You paste an article, hit **Analyze**, and you get:

- a verdict: **REAL**, **FAKE**, or **UNCERTAIN** (when it's near the 50/50 line, it says so instead of pretending to be sure)
- a confidence bar
- the top words that pushed the result toward fake and toward real
- a couple of buttons to correct it ("this was actually Real / Fake") which saves the example so you can retrain on it later

There are three tabs: **Detect**, **History** (your last 20 checks, kept in the browser), and **About**.

---

## How it actually works

No magic here. Three steps:

1. **Words → numbers (TF-IDF).** The text is turned into a long vector of numbers, one per word/phrase the model knows. Common words like "the" get squashed; distinctive ones like "miracle", "Reuters" or "Senate" get weighted up.
2. **Score it (Logistic Regression).** During training the model learned a weight for every word — how "fake-ish" it is. To score your article it multiplies each word's number by that weight, adds it all up, and squeezes the total into a 0–100% probability of being fake.
3. **Decide + explain.** Above 60% → REAL or FAKE. Between 40–60% → UNCERTAIN. The "why" words are just the ones that contributed most to the score.

There's a longer write-up in [HOW_IT_WORKS.md](HOW_IT_WORKS.md) if you want the full version.

---

## The data

- **Base dataset:** the Kaggle "Fake News" dataset — about 20,800 labelled articles (`title`, `author`, `text`, and a `label` where 1 = fake/unreliable and 0 = real/reliable). It's roughly 50/50 between the two classes. This is the bulk of what the model learns from.
- **`recent_2026.csv`:** ~300 current (2026) examples I added on top — real news written in a plain wire-service style, and fake news written in the usual clickbait / conspiracy / health-scam style. This is what gives the model some idea of 2026 topics and vocabulary that the 2017 Kaggle data never had.
- **`feedback.csv`:** anything you label inside the app ends up here, so it can be folded into the next retrain.

On a held-out split the model sits around **97–98% accuracy**. Worth saying plainly: that number is on data that looks like the training data. On random articles from the open web it will do worse, especially on anything short or unusual.

> The base `train.csv` is large (~100 MB) and isn't committed to this repo. Grab it from Kaggle and drop it into a `dataset/` folder if you want to retrain. The app itself runs fine without it because the trained model (`model/pipeline.pkl`) is included.

---

## Running it

You need Python 3.10 or newer.

The easy way on Windows — just double-click **`run.bat`**. It creates the virtual environment the first time, installs what it needs, opens your browser and starts the server.

Or do it by hand:

```bash
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt   # Windows
# source venv/bin/activate && pip install -r requirements.txt # macOS/Linux
python app.py
```

Then open http://127.0.0.1:5000

---

## Keeping it current (the "does it know 2026?" question)

Short answer: a model only knows what it was trained on. There's no trick that makes it magically aware of this year's news — you have to feed it recent, labelled examples and retrain. So that's built in.

There are two ways data gets in:

- editing/extending **`recent_2026.csv`** (or regenerating it with `seed_recent.py`)
- clicking the **Real / Fake** buttons under any result, which appends to **`feedback.csv`**

Then you retrain:

```bash
# one-time: training needs pandas, which the app itself doesn't
venv\Scripts\python.exe -m pip install -r requirements-dev.txt

venv\Scripts\python.exe update_model.py
```

`update_model.py` retrains on the base dataset plus everything in `recent_2026.csv` and `feedback.csv` (recent rows are repeated a few times so a handful of new examples actually move the needle instead of drowning under 20,000 old ones). Restart the app afterwards. If you want it to stay current long-term, the honest answer is to do this on a schedule and keep adding fresh examples.

To retrain only on the base Kaggle data:

```bash
venv\Scripts\python.exe train_model.py
```

---

## Project layout

```
app.py              the Flask server + the analyze() function
train_model.py      train from scratch on the base dataset
update_model.py     retrain including recent_2026.csv + feedback.csv
seed_recent.py      builds recent_2026.csv
recent_2026.csv     current 2026 examples
model/pipeline.pkl  the trained vectorizer + model (ships with the repo)
templates/          the web page
static/             css + js
run.bat             one-click launcher (Windows)
HOW_IT_WORKS.md     longer explanation of the model
```

---

## What it can't do (please read this)

This thing judges **writing style, not facts.** It learned what fake and real articles tend to *sound* like; it has no idea whether a claim is actually true. That means:

- a lie written calmly in a serious, news-y tone can come back as REAL
- a true story written in breathless ALL-CAPS can come back as FAKE
- it's English-only and leans toward the topics it was trained on
- short snippets (a single headline) aren't enough — it'll warn you and the result won't mean much

So treat it as a rough signal and a demo of how text classification works, not as a fact-checker. If something's important, check it against real sources.

---

## Credit

The original idea and the base dataset come from
[abiek12/Fake-News-Detection-using-MachineLearning](https://github.com/abiek12/Fake-News-Detection-using-MachineLearning).
This version is a rebuild with a retrained model, a new UI, the explainability bits, and the update pipeline.
