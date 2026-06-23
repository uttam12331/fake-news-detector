import io

from pypdf import PdfReader

from pdf_toolkit import watermark


def test_add_text_watermark_preserves_page_count(pdf_factory):
    doc = pdf_factory(3)
    result = watermark.add_text_watermark(doc, "CONFIDENTIAL")
    reader = PdfReader(io.BytesIO(result))
    assert len(reader.pages) == 3


def test_add_text_watermark_keeps_original_text(pdf_factory):
    doc = pdf_factory(1, label_prefix="P")
    result = watermark.add_text_watermark(doc, "CONFIDENTIAL")
    reader = PdfReader(io.BytesIO(result))
    assert "P 1" in reader.pages[0].extract_text()
