from __future__ import annotations

from video_annotator import prompts, transcribe, video_io
from video_annotator.config import AnnotatorConfig
from video_annotator.formatting import coerce_format
from video_annotator.types import AnswerFormat, AnswerType, FrameCaption, VideoAnswer, VideoContext
from video_annotator.vision_backend import OllamaBackend


class VideoAnnotator:
    """Local-LLM video annotation/Q&A model.

    Pipeline: sample frames -> caption each frame with a local vision-language model
    (via Ollama) -> transcribe audio locally (faster-whisper) -> hand the combined
    context plus the caller's question/instructions/format to the LLM for the final
    answer. Nothing leaves the machine; no cloud API calls are made.
    """

    def __init__(self, config: AnnotatorConfig | None = None, backend: OllamaBackend | None = None):
        self.config = config or AnnotatorConfig()
        self.backend = backend or OllamaBackend(self.config.ollama_host, self.config.request_timeout_s)

    def build_context(self, video_path: str) -> VideoContext:
        """Run the (expensive) extraction step once; reuse the result for multiple ask() calls."""
        duration = video_io.get_duration_s(video_path)
        raw_frames = video_io.sample_frames(
            video_path, interval_s=self.config.frame_interval_s, max_frames=self.config.max_frames
        )
        captions = [
            FrameCaption(
                timestamp_s=frame.timestamp_s,
                caption=self.backend.generate_with_image(
                    self.config.vision_model,
                    video_io.encode_frame_jpeg(frame.image),
                    prompts.FRAME_CAPTION_PROMPT,
                ),
            )
            for frame in raw_frames
        ]
        transcript = transcribe.transcribe(video_path, self.config.whisper_model)
        return VideoContext(
            video_path=video_path,
            duration_s=duration,
            frame_captions=captions,
            transcript=transcript,
        )

    def ask(
        self,
        video_path: str,
        *,
        question: str | None = None,
        instructions: str | None = None,
        answer_type: AnswerType | str = AnswerType.DESCRIPTION,
        answer_format: AnswerFormat | str = AnswerFormat.TEXT,
        context: VideoContext | None = None,
    ) -> VideoAnswer:
        """Answer a question about the video, or describe it if none is given.

        - question: a specific thing to ask about the video content.
        - instructions: how to frame the answer (e.g. "focus on safety hazards") when
          there isn't a single question.
        - answer_type / answer_format: what kind of answer and in what shape.
        - context: reuse a VideoContext from a prior build_context() call to avoid
          re-running frame sampling/transcription on the same video.
        """
        answer_type = AnswerType(answer_type)
        answer_format = AnswerFormat(answer_format)

        if question and answer_type == AnswerType.DESCRIPTION:
            answer_type = AnswerType.QA

        ctx = context or self.build_context(video_path)

        prompt = prompts.build_answer_prompt(
            subject="video",
            context_text=ctx.render(),
            answer_type=answer_type,
            answer_format=answer_format,
            question=question,
            instructions=instructions,
        )
        raw_answer = self.backend.generate(self.config.text_model, prompt)
        answer = coerce_format(raw_answer, answer_format)

        return VideoAnswer(
            answer=answer,
            answer_type=answer_type,
            answer_format=answer_format,
            question=question,
            instructions=instructions,
            frames_analyzed=len(ctx.frame_captions),
            had_transcript=bool(ctx.transcript.strip()),
        )
