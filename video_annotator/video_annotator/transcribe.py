from __future__ import annotations

_MODEL_CACHE: dict[str, object] = {}


def transcribe(video_path: str, model_size: str = "base") -> str:
    """Local speech-to-text on the video's audio track via faster-whisper.

    Returns "" (not an error) when the video has no audio track or no speech --
    callers should treat a missing transcript as normal, not exceptional.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "faster-whisper is required for audio transcription. "
            "Install it with: pip install faster-whisper"
        ) from exc

    model = _MODEL_CACHE.get(model_size)
    if model is None:
        model = WhisperModel(model_size, device="auto", compute_type="auto")
        _MODEL_CACHE[model_size] = model

    try:
        segments, _info = model.transcribe(video_path, vad_filter=True)
        return " ".join(seg.text.strip() for seg in segments).strip()
    except Exception:
        # No audio stream, corrupt/unsupported container, etc. -- silence is a
        # valid outcome for a muted clip, so degrade to "" rather than fail the
        # whole annotation pipeline over a missing audio track.
        return ""
