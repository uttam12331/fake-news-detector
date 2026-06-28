# Projects

Standalone apps and tools built alongside the main Fake News Detector (which
lives at the repository root). Each project here is fully self-contained — its
own dependencies, tests, and a detailed `README.md` inside its folder. This
page is the index: what each one is, and the shortest path to running it.

| Project | What it is | Stack |
|---|---|---|
| [`fake_call/`](fake_call/) | Simulated incoming-call app + phone-number lookup, with an Android `.apk` build | Flask + PWA, Android WebView |
| [`parakeet_clone/`](parakeet_clone/) | "Copilot Live" — real-time AI answer assistant for meetings/interviews | Flask + browser Web Speech, bring-your-own LLM key |
| [`pdf_toolkit/`](pdf_toolkit/) | iLovePDF-style PDF editor (merge/split/rotate/protect/watermark/compress) | Python library + Flask + PWA |
| [`video_annotator/`](video_annotator/) | Local video/audio/image annotation & Q&A models | Python + Ollama (fully offline) |

---

## fake_call

Type any caller name, pick a delay, and your phone "rings" with a simulated
incoming call — synthesized ringtone, vibration, an authentic full-screen call
UI, and an optional fake voice that talks back when you accept. A second tab
looks up a phone number's carrier / line type / location (bring-your-own API
key). Ships a real Android `.apk` via GitHub Actions. Nothing actually dials —
it's all simulated.

```bash
cd projects/fake_call
pip install -r requirements.txt
python -m flask --app app.server run --port 5057   # then open http://localhost:5057
```

Tests: `node tests/test_callsim.mjs && node tests/test_fakevoice.mjs && python -m pytest tests/test_lookup.py`

For the Android `.apk`: push the branch and grab the `app-debug.apk` artifact
from the **Build Fake Call APK** GitHub Actions run (the Android SDK can't be
built in this sandbox; CI builds it). Details in [`fake_call/README.md`](fake_call/README.md).

## parakeet_clone (Copilot Live)

A meeting/interview copilot: it transcribes live speech for free in the browser
(Web Speech API, no key), then streams an AI answer. Can also capture on-screen
screenshots as context and describe an uploaded video. You paste your own
Anthropic or OpenAI key in Settings — it's stored only in your browser and sent
straight to the provider.

```bash
cd projects/parakeet_clone
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app/server.py
```

Details in [`parakeet_clone/README.md`](parakeet_clone/README.md).

## pdf_toolkit

An iLovePDF-style PDF editor: merge, split, reorder/delete/extract pages,
rotate, password protect/unlock, watermark, image↔PDF conversion, and
compress-to-a-target-size. The core logic is a Flask-independent library
(`pdf_toolkit/`) with a pytest suite; `app/` wraps it in a Flask web app that's
installable as a PWA.

```bash
cd projects/pdf_toolkit
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest tests/ -q
python app/server.py        # then open http://localhost:5050
```

Details in [`pdf_toolkit/README.md`](pdf_toolkit/README.md).

## video_annotator

Three independent local-LLM models — one each for **video**, **audio**, and
**images** — that describe, summarize, answer questions about, timeline, or
fact-check a file. Everything runs locally: frame captioning and audio
transcription happen on your machine, and LLM calls go to a local
[Ollama](https://ollama.com) server. No cloud keys, no data leaves the box.

```bash
# Requires Ollama running locally with a vision model pulled:
ollama serve &
ollama pull qwen2.5vl:7b

cd projects/video_annotator
pip install -r requirements.txt
python -m video_annotator.cli video.mp4 -q "What is the person wearing?"
```

Details (CLI flags, Python API, model choices) in [`video_annotator/README.md`](video_annotator/README.md).
