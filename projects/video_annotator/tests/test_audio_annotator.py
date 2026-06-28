import json

import pytest

from conftest import FakeBackend
from video_annotator import transcribe as transcribe_module
from video_annotator.audio_annotator import AudioAnnotator
from video_annotator.config import AnnotatorConfig
from video_annotator.types import AnswerFormat, AnswerType, AudioContext, TranscriptSegment


@pytest.fixture
def audio_file(tmp_path):
    path = tmp_path / "clip.wav"
    path.write_bytes(b"not real audio, just needs to exist")
    return str(path)


def make_context(audio_path="clip.wav"):
    return AudioContext(
        audio_path=audio_path,
        duration_s=5.0,
        segments=[
            TranscriptSegment(0.0, 2.0, "hello there"),
            TranscriptSegment(2.0, 5.0, "this is a test recording"),
        ],
    )


def test_default_description_has_no_question_or_instructions():
    backend = FakeBackend()
    annotator = AudioAnnotator(AnnotatorConfig(), backend)

    result = annotator.ask("clip.wav", context=make_context())

    assert result.answer_type == AnswerType.DESCRIPTION
    assert "No specific question or instructions" in backend.last_prompt


def test_question_switches_to_qa_type():
    backend = FakeBackend()
    annotator = AudioAnnotator(AnnotatorConfig(), backend)

    result = annotator.ask("clip.wav", question="what did the speaker say?", context=make_context())

    assert result.answer_type == AnswerType.QA
    assert "what did the speaker say?" in backend.last_prompt


def test_timeline_type_sees_timestamped_segments_in_prompt():
    backend = FakeBackend()
    annotator = AudioAnnotator(AnnotatorConfig(), backend)

    annotator.ask("clip.wav", answer_type=AnswerType.TIMELINE, context=make_context())

    assert "2.0" in backend.last_prompt
    assert "hello there" in backend.last_prompt


def test_json_format_wraps_non_json_response():
    backend = FakeBackend(response="just plain text")
    annotator = AudioAnnotator(AnnotatorConfig(), backend)

    result = annotator.ask("clip.wav", answer_format=AnswerFormat.JSON, context=make_context())

    assert json.loads(result.answer) == {"answer": "just plain text"}


def test_segments_analyzed_reflects_context():
    backend = FakeBackend()
    annotator = AudioAnnotator(AnnotatorConfig(), backend)

    result = annotator.ask("clip.wav", context=make_context())

    assert result.segments_analyzed == 2


def test_missing_file_raises_file_not_found():
    annotator = AudioAnnotator(AnnotatorConfig(), FakeBackend())
    with pytest.raises(FileNotFoundError):
        annotator.build_context("/nonexistent/clip.wav")


def test_build_context_uses_transcribe_segments(monkeypatch, audio_file):
    monkeypatch.setattr(
        transcribe_module,
        "transcribe_segments",
        lambda path, size: [TranscriptSegment(0.0, 1.5, "hi")],
    )

    annotator = AudioAnnotator(AnnotatorConfig(), FakeBackend())
    ctx = annotator.build_context(audio_file)

    assert ctx.duration_s == 1.5
    assert ctx.transcript == "hi"
