"""
Refresh the model with CURRENT data — this is how the detector "learns 2026".

It retrains the same TF-IDF + LogisticRegression pipeline on:
  1. the original Kaggle training set (the bulk of the signal), PLUS
  2. recent_2026.csv      (current labelled examples — see seed_recent.py), PLUS
  3. feedback.csv         (examples you labelled inside the app, if any).

Recent rows are up-weighted (duplicated) so a small number of current examples actually
shift the model instead of being drowned out by 20,000 old ones. Run this whenever you add
new data, then restart the app.

    python update_model.py
"""
import os
import pickle

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

HERE = os.path.dirname(os.path.abspath(__file__))


def _find_base():
    """Look for the Kaggle train.csv locally first, then in the sibling original repo."""
    candidates = [
        os.path.join(HERE, "dataset", "train.csv"),
        os.path.join(HERE, "..", "Fake-News-Detection-using-MachineLearning",
                     "dataset", "train.csv"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    raise FileNotFoundError(
        "Could not find the base dataset. Download train.csv from the Kaggle 'Fake News' "
        "dataset and place it in a 'dataset/' folder next to this script."
    )


BASE = _find_base()
RECENT = os.path.join(HERE, "recent_2026.csv")
FEEDBACK = os.path.join(HERE, "feedback.csv")
OUT = os.path.join(HERE, "model", "pipeline.pkl")

# How many times to repeat each recent/feedback row so it carries real weight.
# Enough that recent terms clear the vectorizer's min_df and shift the model, but small
# enough not to skew general predictions (a few dozen rows shouldn't dominate ~20k).
RECENT_WEIGHT = 12


def load_base():
    df = pd.read_csv(BASE).fillna("")
    df["content"] = (df["title"] + " " + df["text"]).str.strip()
    df = df[df["content"].str.len() > 0]
    return df[["content", "label"]]


def load_extra(path, name):
    if not os.path.exists(path):
        print(f"  ({name}: not found, skipping)")
        return None
    df = pd.read_csv(path).fillna("")
    df = df.rename(columns={"text": "content"})
    df = df[df["content"].str.strip().str.len() > 0]
    df["label"] = df["label"].astype(int)
    print(f"  {name}: {len(df)} rows (x{RECENT_WEIGHT} weight)")
    return pd.concat([df[["content", "label"]]] * RECENT_WEIGHT, ignore_index=True)


def main():
    print("Loading data...")
    parts = [load_base()]
    print(f"  base dataset: {len(parts[0])} rows")
    for path, name in [(RECENT, "recent_2026.csv"), (FEEDBACK, "feedback.csv")]:
        extra = load_extra(path, name)
        if extra is not None:
            parts.append(extra)

    data = pd.concat(parts, ignore_index=True)
    X, y = data["content"], data["label"].astype(int)
    print(f"Total training rows (with weighting): {len(data)}")

    vectorizer = TfidfVectorizer(
        stop_words="english", ngram_range=(1, 2),
        max_features=50000, min_df=3, sublinear_tf=True,
    )
    print("Vectorizing + training...")
    Xv = vectorizer.fit_transform(X)
    clf = LogisticRegression(C=4.0, max_iter=1000)
    clf.fit(Xv, y)

    with open(OUT, "wb") as f:
        pickle.dump({"vectorizer": vectorizer, "model": clf}, f)
    print("Updated model saved ->", OUT)
    print("Restart the app to use the refreshed model.")


if __name__ == "__main__":
    main()
