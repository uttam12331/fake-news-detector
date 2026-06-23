import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from video_annotator import image_io


def test_load_image_bytes_round_trips(tmp_path):
    path = str(tmp_path / "photo.png")
    cv2.imwrite(path, np.full((8, 8, 3), 42, dtype=np.uint8))

    data = image_io.load_image_bytes(path)

    assert isinstance(data, bytes)
    assert len(data) > 0


def test_missing_file_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        image_io.load_image_bytes("/nonexistent/photo.png")


def test_empty_file_raises_value_error(tmp_path):
    path = tmp_path / "empty.png"
    path.write_bytes(b"")
    with pytest.raises(ValueError):
        image_io.load_image_bytes(str(path))


def test_corrupt_file_raises_value_error(tmp_path):
    path = tmp_path / "corrupt.png"
    path.write_bytes(b"this is not an image")
    with pytest.raises(ValueError):
        image_io.load_image_bytes(str(path))
