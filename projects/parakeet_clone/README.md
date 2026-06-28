# Copilot Live

A real-time AI answer assistant — a meeting / interview copilot in the spirit
of tools like ParakeetAI. It listens to live speech, transcribes it for free in
the browser, and streams an AI-generated answer. It also takes on-screen
screenshots as context and can describe an uploaded video.

This is an independent implementation (all original code and branding); it
reproduces the *functionality*, not any other product's code or assets.

## What it does

- **Live Copilot** — start listening; the question is transcribed in real time
  (browser Web Speech API, free, no key). Stop to auto-answer the whole
  transcript, or hit "Answer now" mid-stream. Answers stream in token-by-token.
- **Record & Ask** — one big record button. Speak, tap to stop, and it
  transcribes + sends automatically. If no context is attached, it asks whether
  to grab a screenshot first.
- **Describe Video** — share/upload a video; it samples evenly-spaced frames and
  asks a multimodal model to describe it. Give instructions for what/how to
  describe, or it prompts you.
- **Context screenshots** — the 📸 button captures your screen (a coding
  problem, a slide, a chat). Capture several for long context; **all** of them
  are sent with the question.
- **Personas** — Interview Copilot, Meeting Assistant, Sales Call, or General
  Q&A, each with an editable system prompt. Plus a background-notes/résumé field
  that's sent as context.

## Provider & key

You paste your own API key in **Settings**. It's stored only in your browser
(`localStorage`) and sent **directly** to the provider — there is no server of
ours in between.

- **Claude (Anthropic)** — Opus 4.8 / Sonnet 4.6 / Haiku 4.5
- **OpenAI** — GPT-4o / GPT-4o mini

Both support image input (used for screenshots and video frames) and streaming.

## Run it

```bash
cd parakeet_clone
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app/server.py
```

Open **http://localhost:5060** in Chrome or Edge.

> **Why a server and not just a file?** Microphone, screen-capture, and speech
> recognition require a *secure context*. `http://localhost` qualifies;
> `file://` does not. So open it via the local server, not by double-clicking
> the HTML.

## Tests

```bash
node tests/test_providers.mjs
```

Covers request building for both providers (incl. multimodal image blocks),
auth headers, and SSE stream assembly against a mocked response.

## Browser support

Built for desktop **Chrome / Edge**. Speech recognition and screen capture
(`getDisplayMedia`) are not available on most mobile browsers, so the live/
record/screenshot features are desktop-first; video-describe works anywhere the
browser can decode the video.
