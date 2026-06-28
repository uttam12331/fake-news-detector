from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RawFrame:
    timestamp_s: float
    image: "object"  # numpy ndarray (BGR), kept untyped here to avoid a hard cv2 import


def get_duration_s(video_path: str) -> float:
    cv2 = _cv2()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    cap.release()
    if fps <= 0:
        return 0.0
    return frame_count / fps


def sample_frames(video_path: str, interval_s: float, max_frames: int) -> list[RawFrame]:
    """Pull evenly-spaced frames from the video for the vision model to caption."""
    cv2 = _cv2()
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    if fps <= 0:
        cap.release()
        raise ValueError(f"Could not read frame rate for: {video_path}")

    step = max(1, round(fps * interval_s))
    frames: list[RawFrame] = []
    idx = 0
    while len(frames) < max_frames:
        ok = cap.grab()
        if not ok:
            break
        if idx % step == 0:
            ok, image = cap.retrieve()
            if not ok:
                break
            frames.append(RawFrame(timestamp_s=idx / fps, image=image))
        idx += 1
    cap.release()
    return frames


def encode_frame_jpeg(image) -> bytes:
    cv2 = _cv2()
    ok, buf = cv2.imencode(".jpg", image)
    if not ok:
        raise ValueError("Failed to encode frame as JPEG")
    return bytes(buf)


def _cv2():
    try:
        import cv2  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "opencv-python-headless is required for frame extraction. "
            "Install it with: pip install opencv-python-headless"
        ) from exc
    return cv2
