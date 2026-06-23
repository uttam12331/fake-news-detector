import json

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from conftest import FakeBackend
from video_annotator.config import AnnotatorConfig
from video_annotator.image_annotator import ImageAnnotator
from video_annotator.types import AnswerFormat, AnswerType


@pytest.fixture
def synthetic_image(tmp_path):
    path = str(tmp_path / "photo.jpg")
    cv2.imwrite(path, np.full((8, 8, 3), 100, dtype=np.uint8))
    return path


def test_default_description_has_no_question_or_instructions(synthetic_image):
    backend = FakeBackend()
    annotator = ImageAnnotator(AnnotatorConfig(), backend)

    result = annotator.ask(synthetic_image)

    assert result.answer_type == AnswerType.DESCRIPTION
    assert result.question is None
    assert "No specific question or instructions" in backend.last_prompt
    assert backend.images_seen  # the raw image bytes were actually sent to the model


def test_question_switches_to_qa_type(synthetic_image):
    backend = FakeBackend()
    annotator = ImageAnnotator(AnnotatorConfig(), backend)

    result = annotator.ask(synthetic_image, question="what color is this?")

    assert result.answer_type == AnswerType.QA
    assert "what color is this?" in backend.last_prompt


def test_instructions_are_passed_through(synthetic_image):
    backend = FakeBackend()
    annotator = ImageAnnotator(AnnotatorConfig(), backend)

    result = annotator.ask(synthetic_image, instructions="focus on any text visible")

    assert result.instructions == "focus on any text visible"
    assert "focus on any text visible" in backend.last_prompt


def test_json_format_is_always_valid_json(synthetic_image):
    backend = FakeBackend(response="not json at all")
    annotator = ImageAnnotator(AnnotatorConfig(), backend)

    result = annotator.ask(synthetic_image, answer_format=AnswerFormat.JSON)

    assert json.loads(result.answer) == {"answer": "not json at all"}


def test_missing_image_raises_file_not_found():
    annotator = ImageAnnotator(AnnotatorConfig(), FakeBackend())
    with pytest.raises(FileNotFoundError):
        annotator.ask("/nonexistent/photo.jpg")
