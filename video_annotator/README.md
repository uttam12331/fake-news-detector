# Video Annotator

A local-LLM video annotation / Q&A model. Point it at a video and it can:

- give a general **description** of what's in it
- **summarize** it
- answer a **specific question** about its content
- break it down as a **timeline** (timestamp -> what happens)
- run a **fact-check** style verdict against a claim, using the video as evidence

You control:
- **what kind of answer** (`description` / `summary` / `qa` / `timeline` / `fact_check`)
- **what format** it comes back in (`text` / `markdown` / `bullets` / `json`)
- **a specific question**, and/or free-text **instructions** for how to frame the answer

If you don't give a question or instructions, it says so and falls back to a general
description instead of guessing what you wanted.

Everything runs **locally** — frame captioning and audio transcription happen on your
machine, and the LLM calls go to a local [Ollama](https://ollama.com) server. No cloud
API keys, no data leaves the box. This is a separate module inside this repo and doesn't
touch the fake-news-detector app (`app.py`, `model/`, etc.).

## How it works

1. **Sample frames** from the video at a configurable interval (`video_io.py`, OpenCV).
2. **Caption each frame** with a local vision-language model via Ollama
   (`vision_backend.py`).
3. **Transcribe the audio** locally with `faster-whisper` (`transcribe.py`) — empty
   string if the clip has no speech/audio, which is a normal outcome, not an error.
4. **Combine** frame captions + transcript into one text context (`types.py`).
5. **Answer**: build a prompt from the context + your question/instructions/type/format
   and run it through the local LLM (`prompts.py`, `annotator.py`).

```
video.mp4 -> [sample frames] -> [caption each frame]  \
                                                         -> [context] -> [LLM answer]
          -> [transcribe audio] --------------------- /
```

## Setup

```bash
# 1. Install Ollama and start the server: https://ollama.com/download
ollama serve &

# 2. Pull a local vision-language model (pick one that fits your hardware/quality needs,
#    see "Choosing a model" below)
ollama pull qwen2.5vl:7b

# 3. Install Python deps
cd video_annotator
pip install -r requirements.txt
```

## Usage

### CLI

```bash
# General description (no question given)
python -m video_annotator.cli video.mp4

# Ask something specific
python -m video_annotator.cli video.mp4 -q "What is the person wearing?"

# Timeline, as markdown
python -m video_annotator.cli video.mp4 -t timeline -f markdown

# Fact-check a claim against the video, as JSON
python -m video_annotator.cli video.mp4 \
  -t fact_check -f json \
  -q "The video shows the building was already on fire before the truck arrived."

# Steer a description without a single question
python -m video_annotator.cli video.mp4 -i "focus on any safety violations you see"
```

### Python API

```python
from video_annotator import VideoAnnotator, AnswerType, AnswerFormat

annotator = VideoAnnotator()  # uses default AnnotatorConfig

# Build the (expensive) context once, reuse it for multiple questions on the same video
context = annotator.build_context("video.mp4")

result = annotator.ask(
    "video.mp4",
    question="Does anyone mention a date in the video?",
    answer_type=AnswerType.QA,
    answer_format=AnswerFormat.TEXT,
    context=context,
)
print(result.answer)

summary = annotator.ask("video.mp4", answer_type=AnswerType.SUMMARY, context=context)
print(summary.answer)
```

### Configuration

```python
from video_annotator import VideoAnnotator, AnnotatorConfig

config = AnnotatorConfig(
    vision_model="qwen2.5vl:7b",
    text_model="qwen2.5vl:7b",
    whisper_model="small",
    frame_interval_s=1.0,
    max_frames=64,
)
annotator = VideoAnnotator(config)
```

## Choosing a model (production notes)

These run fully offline via Ollama. Pick based on your accuracy/latency/VRAM budget:

| Model | Notes |
|---|---|
| `qwen2.5vl:7b` | Strong general video/image understanding, good OCR, reasonable on a single consumer GPU. Good default. |
| `qwen2.5vl:32b` / `72b` | Noticeably better reasoning and detail; needs serious GPU/multi-GPU. |
| `llava:13b` / `llava:34b` | Widely used, solid baseline, slightly weaker than Qwen2.5-VL on fine detail/OCR. |
| `minicpm-v` | Good quality at a small size; decent option for CPU-only or edge deployment. |

For production throughput, run Ollama with a model that fits comfortably in GPU memory,
and tune `frame_interval_s` / `max_frames` — fewer, well-chosen frames means fewer
vision-model calls and lower latency per video. `whisper_model="small"` or `"medium"`
is a good accuracy/speed tradeoff for transcription; `"large-v3"` is most accurate but
slower.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Tests mock the Ollama backend (no server/model required) and exercise real frame
extraction against synthetically generated video files (no fixture files needed).
