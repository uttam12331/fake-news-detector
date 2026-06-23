import io

import pytest
from PIL import Image
from reportlab.pdfgen import canvas


def make_pdf_bytes(num_pages: int = 1, *, label_prefix: str = "Page") -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(300, 400))
    for i in range(num_pages):
        c.drawString(50, 200, f"{label_prefix} {i + 1}")
        c.showPage()
    c.save()
    return buffer.getvalue()


def make_pdf_with_image_bytes(*, image_size=(800, 600), color=(200, 50, 50)) -> bytes:
    img_buffer = io.BytesIO()
    Image.new("RGB", image_size, color).save(img_buffer, format="JPEG", quality=95)
    img_buffer.seek(0)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(612, 792))
    from reportlab.lib.utils import ImageReader

    c.drawImage(ImageReader(img_buffer), 0, 0, width=600, height=450)
    c.showPage()
    c.save()
    return buffer.getvalue()


def make_image_bytes(*, size=(100, 100), color=(10, 200, 30), fmt="JPEG") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, format=fmt)
    return buffer.getvalue()


@pytest.fixture
def pdf_factory():
    return make_pdf_bytes


@pytest.fixture
def pdf_with_image_factory():
    return make_pdf_with_image_bytes


@pytest.fixture
def image_factory():
    return make_image_bytes
