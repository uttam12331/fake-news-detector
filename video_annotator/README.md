# Video / Audio / Image Annotator

Three separate local-LLM annotation/Q&A models — one each for **video**, **audio**, and
**images**. Point any of them at a file and they can:

- give a general **description** of what's in it
- **summarize** it
- answer a **specific question** about its content
- break it down as a **timeline** (timestamp -> what happens) — video/audio only
- run a **fact-check** style verdict against a claim, using the content as evidence

You control:
- **what kind of answer** (`description` / `summary` / `qa` / `timeline` / `fact_check`)
- **what format** it comes back in (`text` / `markdown` / `bullets` / `json`)
- **a specific question**, and/or free-text **instructions** for how to frame the answer

If you don't give a question or instructions, it says so and falls back to a general
description instead of guessing what you wanted.

Everything runs **locally** — frame/image captioning and audio transcription happen on
your machine, and the LLM calls go to a local [Ollama](https://ollama.com) server. No
cloud API keys, no data leaves the box. This is a separate module inside this repo and
doesn't touch the fake-news-detector app (`app.py`, `model/`, etc.).

## The three models

They're independent — each has its own class, CLI, and answer type — because the
pipeline for each medium is genuinely different:

| | `VideoAnnotator` | `AudioAnnotator` | `ImageAnnotator` |
|---|---|---|---|
| Input | video file | audio file | image file |
| Extraction | sampled frames + audio transcript | timestamped transcript | none (sent as-is) |
| Vision-model calls | one per sampled frame (captioning) | none | one (direct Q&A on the image) |
| Text-model call | one (synthesize answer from frames+transcript) | one (synthesize answer from transcript) | — (vision model answers directly) |
| Extra result field | `frames_analyzed`, `had_transcript` | `segments_analyzed` | — |

They share the same config (`AnnotatorConfig`), prompt-building rules, and JSON-format
enforcement (`prompts.py`, `formatting.py`) so the behavior of "no question given" or
"format=json" is consistent across all three.

## How each one works

**Video** (`annotator.py`):
1. **Sample frames** from the video at a configurable interval (`video_io.py`, OpenCV).
2. **Caption each frame** with a local vision-language model via Ollama (`vision_backend.py`).
3. **Transcribe the audio** locally with `faster-whisper` (`transcribe.py`) — empty
   string if the clip has no speech/audio, which is a normal outcome, not an error.
4. **Combine** frame captions + transcript into one text context.
5. **Answer**: build a prompt from the context + your question/instructions/type/format
   and run it through the local LLM.

```
video.mp4 -> [sample frames] -> [caption each frame]  \
                                                         -> [context] -> [LLM answer]
          -> [transcribe audio] --------------------- /
```

**Audio** (`audio_annotator.py`):
1. **Transcribe** locally with `faster-whisper`, keeping per-segment timestamps.
2. **Answer**: build a prompt from the timestamped transcript + your
   question/instructions/type/format and run it through the local LLM.

```
clip.wav -> [transcribe with timestamps] -> [context] -> [LLM answer]
```

**Image** (`image_annotator.py`):
1. **Load** the image file (`image_io.py`, validated, no re-encoding).
2. **Answer**: one call straight to the local vision-language model with the image
   attached and your question/instructions/type/format in the prompt — no separate
   captioning pass, since the model can just look at the image while answering.

```
photo.jpg -> [load + validate] -> [LLM answer, image attached]
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

Each medium has its own command:

```bash
# Video -- general description (no question given)
python -m video_annotator.cli video.mp4

# Video -- ask something specific
python -m video_annotator.cli video.mp4 -q "What is the person wearing?"

# Video -- timeline, as markdown
python -m video_annotator.cli video.mp4 -t timeline -f markdown

# Video -- fact-check a claim against the video, as JSON
python -m video_annotator.cli video.mp4 \
  -t fact_check -f json \
  -q "The video shows the building was already on fire before the truck arrived."

# Audio -- ask something specific
python -m video_annotator.audio_cli call.wav -q "What did the caller ask for?"

# Audio -- timeline of who said what, when
python -m video_annotator.audio_cli call.wav -t timeline

# Image -- general description (no question given)
python -m video_annotator.image_cli photo.jpg

# Image -- ask something specific
python -m video_annotator.image_cli photo.jpg -q "What text is visible on the sign?"

# Steer a description without a single question (works for all three)
python -m video_annotator.cli video.mp4 -i "focus on any safety violations you see"
```

### Python API

```python
from video_annotator import VideoAnnotator, AudioAnnotator, ImageAnnotator, AnswerType, AnswerFormat

video = VideoAnnotator()  # uses default AnnotatorConfig
context = video.build_context("video.mp4")  # build the (expensive) context once...
result = video.ask(  # ...and reuse it for multiple questions on the same video
    "video.mp4",
    question="Does anyone mention a date in the video?",
    answer_type=AnswerType.QA,
    answer_format=AnswerFormat.TEXT,
    context=context,
)
print(result.answer)

audio = AudioAnnotator()
print(audio.ask("call.wav", question="What did the caller ask for?").answer)

image = ImageAnnotator()
print(image.ask("photo.jpg", instructions="focus on any text visible").answer)
```

### Configuration

All three annotators take the same config:

```python
from video_annotator import VideoAnnotator, AnnotatorConfig

config = AnnotatorConfig(
    vision_model="qwen2.5vl:7b",
    text_model="qwen2.5vl:7b",
    whisper_model="small",
    frame_interval_s=1.0,
    max_frames=64,
)
annotator = VideoAnnotator(config)  # or AudioAnnotator(config) / ImageAnnotator(config)
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

Tests mock the Ollama backend and the faster-whisper model (no server/model required)
and exercise real frame/image extraction against synthetically generated video/image
files (no fixture files needed).
