from __future__ import annotations

from video_annotator.types import TranscriptSegment

_MODEL_CACHE: dict[str, object] = {}


def transcribe_segments(audio_path: str, model_size: str = "base") -> list[TranscriptSegment]:
    """Local speech-to-text via faster-whisper, with per-segment timestamps.

    Returns [] (not an error) when the file has no audio track or no speech --
    callers should treat a missing transcript as normal, not exceptional.
    """
    model = _get_model(model_size)
    try:
        segments, _info = model.transcribe(audio_path, vad_filter=True)
        return [
            TranscriptSegment(start_s=seg.start, end_s=seg.end, text=seg.text.strip())
            for seg in segments
        ]
    except Exception:
        # No audio stream, corrupt/unsupported container, etc. -- silence is a
        # valid outcome for a muted clip, so degrade to [] rather than fail the
        # whole annotation pipeline over a missing audio track.
        return []


def transcribe(audio_path: str, model_size: str = "base") -> str:
    """Same as transcribe_segments(), flattened to a single string."""
    segments = transcribe_segments(audio_path, model_size)
    return " ".join(seg.text for seg in segments).strip()


def _get_model(model_size: str):
    model = _MODEL_CACHE.get(model_size)
    if model is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "faster-whisper is required for audio transcription. "
                "Install it with: pip install faster-whisper"
            ) from exc
        model = WhisperModel(model_size, device="auto", compute_type="auto")
        _MODEL_CACHE[model_size] = model
    return model
