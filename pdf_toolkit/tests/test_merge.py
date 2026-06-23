import pytest
from pypdf import PdfReader
import io

from pdf_toolkit.errors import NoFilesProvidedError
from pdf_toolkit.merge import merge_pdfs


def test_merge_combines_pages_in_order(pdf_factory):
    a = pdf_factory(2, label_prefix="A")
    b = pdf_factory(3, label_prefix="B")

    merged = merge_pdfs([a, b])

    reader = PdfReader(io.BytesIO(merged))
    assert len(reader.pages) == 5


def test_merge_with_no_files_raises():
    with pytest.raises(NoFilesProvidedError):
        merge_pdfs([])


def test_merge_single_file_is_unchanged_page_count(pdf_factory):
    a = pdf_factory(4)
    merged = merge_pdfs([a])
    assert len(PdfReader(io.BytesIO(merged)).pages) == 4
