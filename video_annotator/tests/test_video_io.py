import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from video_annotator import video_io


@pytest.fixture
def synthetic_video(tmp_path):
    path = str(tmp_path / "synthetic.mp4")
    fps = 10
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (16, 16))
    for i in range(30):  # 3 seconds
        frame = np.full((16, 16, 3), i % 256, dtype=np.uint8)
        writer.write(frame)
    writer.release()
    return path


def test_get_duration_s_matches_frame_count_over_fps(synthetic_video):
    duration = video_io.get_duration_s(synthetic_video)
    assert duration == pytest.approx(3.0, abs=0.2)


def test_sample_frames_respects_interval_and_max(synthetic_video):
    frames = video_io.sample_frames(synthetic_video, interval_s=1.0, max_frames=10)
    assert 2 <= len(frames) <= 4
    timestamps = [f.timestamp_s for f in frames]
    assert timestamps == sorted(timestamps)


def test_sample_frames_respects_max_frames_cap(synthetic_video):
    frames = video_io.sample_frames(synthetic_video, interval_s=0.1, max_frames=2)
    assert len(frames) == 2


def test_encode_frame_jpeg_returns_bytes(synthetic_video):
    frames = video_io.sample_frames(synthetic_video, interval_s=1.0, max_frames=1)
    encoded = video_io.encode_frame_jpeg(frames[0].image)
    assert isinstance(encoded, bytes)
    assert encoded[:2] == b"\xff\xd8"  # JPEG magic bytes


def test_get_duration_s_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        video_io.get_duration_s("/nonexistent/path/video.mp4")
