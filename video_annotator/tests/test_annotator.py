import json

import pytest

from video_annotator.annotator import VideoAnnotator
from video_annotator.config import AnnotatorConfig
from video_annotator.types import AnswerFormat, AnswerType, FrameCaption, VideoContext


class FakeBackend:
    """Stands in for OllamaBackend so tests don't need a running Ollama server."""

    def __init__(self, response: str = "a person is talking on camera"):
        self.response = response
        self.captioned: list[bytes] = []
        self.last_prompt: str | None = None

    def caption_frame(self, model, image_jpeg, prompt):
        self.captioned.append(image_jpeg)
        return "a frame caption"

    def generate(self, model, prompt):
        self.last_prompt = prompt
        return self.response


def make_context():
    return VideoContext(
        video_path="clip.mp4",
        duration_s=12.0,
        frame_captions=[FrameCaption(0.0, "a dog runs across a yard")],
        transcript="someone says hello",
    )


def test_default_description_has_no_question_or_instructions():
    backend = FakeBackend()
    annotator = VideoAnnotator(AnnotatorConfig(), backend)

    result = annotator.ask("clip.mp4", context=make_context())

    assert result.answer_type == AnswerType.DESCRIPTION
    assert result.question is None
    assert result.instructions is None
    assert "No specific question or instructions" in backend.last_prompt


def test_question_switches_to_qa_type():
    backend = FakeBackend()
    annotator = VideoAnnotator(AnnotatorConfig(), backend)

    result = annotator.ask("clip.mp4", question="what color is the dog?", context=make_context())

    assert result.answer_type == AnswerType.QA
    assert "what color is the dog?" in backend.last_prompt


def test_explicit_instructions_are_passed_through():
    backend = FakeBackend()
    annotator = VideoAnnotator(AnnotatorConfig(), backend)

    result = annotator.ask(
        "clip.mp4", instructions="focus on background audio", context=make_context()
    )

    assert result.instructions == "focus on background audio"
    assert "focus on background audio" in backend.last_prompt


def test_explicit_answer_type_is_respected_even_with_a_question():
    backend = FakeBackend()
    annotator = VideoAnnotator(AnnotatorConfig(), backend)

    result = annotator.ask(
        "clip.mp4",
        question="did the video accurately depict the event?",
        answer_type=AnswerType.FACT_CHECK,
        context=make_context(),
    )

    assert result.answer_type == AnswerType.FACT_CHECK


@pytest.mark.parametrize("answer_format", list(AnswerFormat))
def test_all_formats_round_trip(answer_format):
    backend = FakeBackend(response="plain text answer")
    annotator = VideoAnnotator(AnnotatorConfig(), backend)

    result = annotator.ask("clip.mp4", answer_format=answer_format, context=make_context())

    assert result.answer_format == answer_format
    if answer_format == AnswerFormat.JSON:
        json.loads(result.answer)  # must always be valid JSON, even if model didn't comply


def test_malformed_json_response_is_wrapped_not_dropped():
    backend = FakeBackend(response="sure, here you go: not actually json")
    annotator = VideoAnnotator(AnnotatorConfig(), backend)

    result = annotator.ask("clip.mp4", answer_format=AnswerFormat.JSON, context=make_context())

    parsed = json.loads(result.answer)
    assert parsed["answer"] == "sure, here you go: not actually json"


def test_well_formed_json_response_passes_through_unwrapped():
    backend = FakeBackend(response='{"verdict": "REAL", "confidence": 0.9}')
    annotator = VideoAnnotator(AnnotatorConfig(), backend)

    result = annotator.ask("clip.mp4", answer_format=AnswerFormat.JSON, context=make_context())

    assert json.loads(result.answer) == {"verdict": "REAL", "confidence": 0.9}


def test_frames_and_transcript_metadata_reflect_context():
    backend = FakeBackend()
    annotator = VideoAnnotator(AnnotatorConfig(), backend)

    result = annotator.ask("clip.mp4", context=make_context())

    assert result.frames_analyzed == 1
    assert result.had_transcript is True


def test_build_context_uses_backend_for_each_sampled_frame(tmp_path, monkeypatch):
    import numpy as np

    from video_annotator import video_io

    fake_frame = video_io.RawFrame(timestamp_s=0.0, image=np.zeros((4, 4, 3), dtype="uint8"))
    monkeypatch.setattr(video_io, "get_duration_s", lambda path: 4.0)
    monkeypatch.setattr(video_io, "sample_frames", lambda path, interval_s, max_frames: [fake_frame] * 3)
    monkeypatch.setattr(video_io, "encode_frame_jpeg", lambda image: b"jpeg-bytes")

    backend = FakeBackend()
    annotator = VideoAnnotator(AnnotatorConfig(), backend)

    import video_annotator.transcribe as transcribe_module

    monkeypatch.setattr(transcribe_module, "transcribe", lambda path, size: "")

    ctx = annotator.build_context("clip.mp4")

    assert len(ctx.frame_captions) == 3
    assert len(backend.captioned) == 3
    assert ctx.transcript == ""
