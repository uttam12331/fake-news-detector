from __future__ import annotations

import io

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas


def add_text_watermark(
    input_bytes: bytes,
    text: str,
    *,
    opacity: float = 0.3,
    font_size: int = 40,
    rotation: float = 45,
    color: tuple[float, float, float] = (0.5, 0.5, 0.5),
) -> bytes:
    """Stamp diagonal text across every page, centered."""
    writer = PdfWriter(clone_from=io.BytesIO(input_bytes))
    for page in writer.pages:
        width, height = float(page.mediabox.width), float(page.mediabox.height)
        overlay = PdfReader(io.BytesIO(_make_overlay(width, height, text, opacity, font_size, rotation, color)))
        page.merge_page(overlay.pages[0])

    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _make_overlay(
    width: float, height: float, text: str, opacity: float, font_size: int, rotation: float,
    color: tuple[float, float, float],
) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(width, height))
    c.saveState()
    c.translate(width / 2, height / 2)
    c.rotate(rotation)
    c.setFillColorRGB(*color)
    c.setFillAlpha(opacity)
    c.setFont("Helvetica-Bold", font_size)
    c.drawCentredString(0, 0, text)
    c.restoreState()
    c.showPage()
    c.save()
    return buffer.getvalue()
