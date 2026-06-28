from __future__ import annotations

import os


def load_image_bytes(image_path: str) -> bytes:
    """Read an image file as-is (no re-encoding) and sanity-check it actually decodes."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Could not find image: {image_path}")
    with open(image_path, "rb") as f:
        data = f.read()
    if not data:
        raise ValueError(f"Image file is empty: {image_path}")
    _validate_decodable(data, image_path)
    return data


def _validate_decodable(data: bytes, image_path: str) -> None:
    import numpy as np

    cv2 = _cv2()
    arr = np.frombuffer(data, dtype=np.uint8)
    decoded = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if decoded is None:
        raise ValueError(f"Could not decode image (unsupported or corrupt file): {image_path}")


def _cv2():
    try:
        import cv2  # noqa: F401
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "opencv-python-headless is required to validate images. "
            "Install it with: pip install opencv-python-headless"
        ) from exc
    return cv2
