import sys
import types

import pytest

from video_annotator import transcribe


class _FakeSegment:
    def __init__(self, start, end, text):
        self.start = start
        self.end = end
        self.text = text


class _FakeWhisperModel:
    """Stands in for faster_whisper.WhisperModel -- no real model weights needed."""

    instances = []

    def __init__(self, model_size, device, compute_type):
        self.model_size = model_size
        _FakeWhisperModel.instances.append(self)

    def transcribe(self, path, vad_filter=True):
        if path == "raises.wav":
            raise RuntimeError("no audio stream")
        if path == "silent.wav":
            return [], object()
        return [_FakeSegment(0.0, 1.0, " hello "), _FakeSegment(1.0, 2.5, "world ")], object()


@pytest.fixture(autouse=True)
def fake_faster_whisper(monkeypatch):
    fake_module = types.ModuleType("faster_whisper")
    fake_module.WhisperModel = _FakeWhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", fake_module)
    transcribe._MODEL_CACHE.clear()
    _FakeWhisperModel.instances.clear()
    yield
    transcribe._MODEL_CACHE.clear()


def test_transcribe_segments_returns_timestamped_segments():
    segments = transcribe.transcribe_segments("clip.wav", "base")

    assert [s.text for s in segments] == ["hello", "world"]
    assert segments[0].start_s == 0.0
    assert segments[1].end_s == 2.5


def test_transcribe_flattens_segments_to_text():
    text = transcribe.transcribe("clip.wav", "base")

    assert text == "hello world"


def test_transcribe_segments_returns_empty_list_on_failure():
    assert transcribe.transcribe_segments("raises.wav", "base") == []


def test_transcribe_returns_empty_string_when_silent():
    assert transcribe.transcribe("silent.wav", "base") == ""


def test_model_is_cached_across_calls():
    transcribe.transcribe_segments("clip.wav", "base")
    transcribe.transcribe_segments("clip.wav", "base")

    assert len(_FakeWhisperModel.instances) == 1
