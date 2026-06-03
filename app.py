"""
FakeNews Detector Pro — a cleaned-up rebuild of the original project.

Improvements over the original repo:
  * Model retrained on the CURRENT scikit-learn (no cross-version unpickle warning).
  * Trained on title + body, so it is far less biased on shorter inputs.
  * LogisticRegression -> real confidence score + word-level explainability.
  * Modern single-page UI with 3 useful tabs (Detect / History / About).
  * Short-text warning, example loader, JSON API.
"""
import os
import re
import csv
import pickle

import numpy as np
from flask import Flask, render_template, request, jsonify

HERE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)

with open(os.path.join(HERE, "model", "pipeline.pkl"), "rb") as f:
    _bundle = pickle.load(f)
VECTORIZER = _bundle["vectorizer"]
MODEL = _bundle["model"]
FEATURES = np.array(VECTORIZER.get_feature_names_out())
COEF = MODEL.coef_[0]  # positive -> pushes toward FAKE (label 1)

# Minimum words before we trust the verdict (headlines are too short to be reliable).
MIN_WORDS = 25


def analyze(text):
    text = (text or "").strip()
    word_count = len(re.findall(r"\b\w+\b", text))
    if word_count == 0:
        return {"error": "Please enter some news text."}

    vec = VECTORIZER.transform([text])
    proba = float(MODEL.predict_proba(vec)[0][1])  # P(fake)
    is_fake = proba >= 0.5
    confidence = proba if is_fake else 1 - proba

    # Near the 50/50 boundary the model is genuinely undecided — don't fake certainty.
    if confidence < 0.60:
        verdict = "UNCERTAIN"
    else:
        verdict = "FAKE" if is_fake else "REAL"

    # Explainability: contribution of each present term = tfidf * coefficient.
    row = vec.tocoo()
    contribs = [(FEATURES[j], row.data[k] * COEF[j]) for k, j in enumerate(row.col)]
    contribs.sort(key=lambda t: t[1])
    real_words = [w for w, c in contribs if c < 0][:6]            # most negative
    fake_words = [w for w, c in reversed(contribs) if c > 0][:6]  # most positive

    warning = None
    if word_count < MIN_WORDS:
        word_label = "word" if word_count == 1 else "words"
        warning = (
            f"Only {word_count} {word_label}. This model reads full articles — short "
            "headlines give unreliable results. Paste a full article for an accurate verdict."
        )

    return {
        "verdict": verdict,
        "leans": "FAKE" if is_fake else "REAL",
        "confidence": round(confidence * 100, 1),
        "fake_probability": round(proba * 100, 1),
        "word_count": word_count,
        "fake_words": fake_words,
        "real_words": real_words,
        "warning": warning,
    }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/predict", methods=["POST"])
def predict():
    data = request.get_json(silent=True) or request.form
    return jsonify(analyze(data.get("text", "")))


FEEDBACK_FILE = os.path.join(HERE, "feedback.csv")


@app.route("/api/feedback", methods=["POST"])
def feedback():
    """Save a user-labelled example so update_model.py can keep the model current.

    This only appends to feedback.csv — it does NOT change the live model until you
    run `python update_model.py`. Core prediction logic is untouched.
    """
    data = request.get_json(silent=True) or request.form
    text = (data.get("text") or "").strip()
    label = str(data.get("label", "")).strip()
    if not text or label not in ("0", "1"):
        return jsonify({"ok": False, "error": "Need text and label (0=real, 1=fake)."}), 400

    new_file = not os.path.exists(FEEDBACK_FILE)
    with open(FEEDBACK_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["text", "label"])
        w.writerow([text, label])
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
