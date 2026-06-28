from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AnnotatorConfig:
    """Tunables for the local inference pipeline.

    All models run locally (via Ollama + faster-whisper) -- no cloud API calls.
    """

    # Ollama model used for per-frame / video captioning and final answer synthesis.
    # Pick any locally-pulled vision-language model, e.g. "qwen2.5vl:7b", "llava:13b",
    # "minicpm-v". Larger models give better captions at the cost of latency.
    vision_model: str = "qwen2.5vl:7b"

    # Ollama model used for the text-only reasoning/answer-synthesis pass once frame
    # captions + transcript are available. Can be the same as vision_model.
    text_model: str = "qwen2.5vl:7b"

    # Ollama server endpoint.
    ollama_host: str = "http://127.0.0.1:11434"

    # faster-whisper model size: tiny/base/small/medium/large-v3.
    whisper_model: str = "base"

    # Seconds between sampled frames. Lower = more detail, slower, more tokens.
    frame_interval_s: float = 2.0

    # Hard cap on number of frames sent to the vision model per video.
    max_frames: int = 32

    # Per-call timeout for Ollama requests, in seconds.
    request_timeout_s: float = 120.0
