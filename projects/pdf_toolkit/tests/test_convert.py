import io

import pytest
from pypdf import PdfReader
from PIL import Image

from pdf_toolkit import convert
from pdf_toolkit.errors import NoFilesProvidedError


def test_images_to_pdf_single_image(image_factory):
    img = image_factory()
    result = convert.images_to_pdf([img])
    reader = PdfReader(io.BytesIO(result))
    assert len(reader.pages) == 1


def test_images_to_pdf_multiple_images(image_factory):
    imgs = [image_factory(color=(255, 0, 0)), image_factory(color=(0, 255, 0))]
    result = convert.images_to_pdf(imgs)
    reader = PdfReader(io.BytesIO(result))
    assert len(reader.pages) == 2


def test_images_to_pdf_no_files_raises():
    with pytest.raises(NoFilesProvidedError):
        convert.images_to_pdf([])


def test_pdf_to_images_returns_one_image_per_page(pdf_factory):
    doc = pdf_factory(3)
    images = convert.pdf_to_images(doc)
    assert len(images) == 3
    for data in images:
        img = Image.open(io.BytesIO(data))
        assert img.format == "PNG"


def test_pdf_to_images_jpeg_format(pdf_factory):
    doc = pdf_factory(1)
    images = convert.pdf_to_images(doc, fmt="jpeg")
    img = Image.open(io.BytesIO(images[0]))
    assert img.format == "JPEG"
