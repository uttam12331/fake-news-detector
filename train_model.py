"""
Train a fake-news classifier on the Kaggle dataset and save a single pipeline.

We train on (title + text) combined so the model has signal from both headlines
and article bodies. We use TF-IDF + LogisticRegression because, unlike the
original PassiveAggressiveClassifier, it gives calibrated-ish probabilities
(a real confidence score) and interpretable coefficients (explainability:
which words pushed the verdict).
"""
import os
import pickle

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

HERE = os.path.dirname(os.path.abspath(__file__))
# Look for the dataset locally first, then in the sibling original repo.
_CANDIDATES = [
    os.path.join(HERE, "dataset", "train.csv"),
    os.path.join(HERE, "..", "Fake-News-Detection-using-MachineLearning",
                 "dataset", "train.csv"),
]
DATASET = next((c for c in _CANDIDATES if os.path.exists(c)), _CANDIDATES[0])
OUT = os.path.join(HERE, "model", "pipeline.pkl")


def main():
    print("Loading dataset:", os.path.abspath(DATASET))
    df = pd.read_csv(DATASET)
    df["title"] = df["title"].fillna("")
    df["text"] = df["text"].fillna("")
    # Combine title + body for richer signal.
    df["content"] = (df["title"] + " " + df["text"]).str.strip()
    df = df[df["content"].str.len() > 0]
    X, y = df["content"], df["label"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    vectorizer = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=50000,
        min_df=3,
        sublinear_tf=True,
    )
    print("Vectorizing...")
    Xtr = vectorizer.fit_transform(X_train)
    Xte = vectorizer.transform(X_test)

    print("Training LogisticRegression...")
    clf = LogisticRegression(C=4.0, max_iter=1000, n_jobs=-1)
    clf.fit(Xtr, y_train)

    pred = clf.predict(Xte)
    acc = accuracy_score(y_test, pred)
    print(f"\nHold-out accuracy: {acc:.4f}")
    print(classification_report(y_test, pred, target_names=["REAL (0)", "FAKE (1)"]))

    with open(OUT, "wb") as f:
        pickle.dump({"vectorizer": vectorizer, "model": clf}, f)
    print("Saved pipeline ->", OUT)


if __name__ == "__main__":
    main()
