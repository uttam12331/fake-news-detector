from __future__ import annotations

import contextlib
import os
import wave

from video_annotator import prompts, transcribe
from video_annotator.config import AnnotatorConfig
from video_annotator.formatting import coerce_format
from video_annotator.types import AnswerFormat, AnswerType, AudioAnswer, AudioContext
from video_annotator.vision_backend import OllamaBackend


class AudioAnnotator:
    """Local-LLM audio annotation/Q&A model.

    Pipeline: transcribe the audio locally (faster-whisper) -> hand the timestamped
    transcript plus the caller's question/instructions/format to a local text LLM
    (via Ollama) for the final answer. Nothing leaves the machine; no cloud API calls
    are made.
    """

    def __init__(self, config: AnnotatorConfig | None = None, backend: OllamaBackend | None = None):
        self.config = config or AnnotatorConfig()
        self.backend = backend or OllamaBackend(self.config.ollama_host, self.config.request_timeout_s)

    def build_context(self, audio_path: str) -> AudioContext:
        """Run the (expensive) transcription step once; reuse the result for multiple ask() calls."""
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Could not find audio file: {audio_path}")
        segments = transcribe.transcribe_segments(audio_path, self.config.whisper_model)
        duration = segments[-1].end_s if segments else _wav_duration_s(audio_path)
        return AudioContext(audio_path=audio_path, duration_s=duration, segments=segments)

    def ask(
        self,
        audio_path: str,
        *,
        question: str | None = None,
        instructions: str | None = None,
        answer_type: AnswerType | str = AnswerType.DESCRIPTION,
        answer_format: AnswerFormat | str = AnswerFormat.TEXT,
        context: AudioContext | None = None,
    ) -> AudioAnswer:
        """Answer a question about the audio, or describe it if none is given.

        - question: a specific thing to ask about what was said/heard.
        - instructions: how to frame the answer (e.g. "focus on the speaker's tone")
          when there isn't a single question.
        - answer_type / answer_format: what kind of answer and in what shape.
        - context: reuse an AudioContext from a prior build_context() call to avoid
          re-transcribing the same file.
        """
        answer_type = AnswerType(answer_type)
        answer_format = AnswerFormat(answer_format)

        if question and answer_type == AnswerType.DESCRIPTION:
            answer_type = AnswerType.QA

        ctx = context or self.build_context(audio_path)

        prompt = prompts.build_answer_prompt(
            subject="audio",
            context_text=ctx.render(),
            answer_type=answer_type,
            answer_format=answer_format,
            question=question,
            instructions=instructions,
        )
        raw_answer = self.backend.generate(self.config.text_model, prompt)
        answer = coerce_format(raw_answer, answer_format)

        return AudioAnswer(
            answer=answer,
            answer_type=answer_type,
            answer_format=answer_format,
            question=question,
            instructions=instructions,
            segments_analyzed=len(ctx.segments),
        )


def _wav_duration_s(audio_path: str) -> float:
    """Best-effort duration when there are no transcript segments to infer it from
    (e.g. silent audio). Only WAV is supported here; non-WAV silent files report 0.0."""
    if not audio_path.lower().endswith(".wav"):
        return 0.0
    try:
        with contextlib.closing(wave.open(audio_path, "rb")) as wf:
            return wf.getnframes() / float(wf.getframerate())
    except Exception:
        return 0.0
