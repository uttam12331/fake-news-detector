import io

import pytest
from pypdf import PdfReader

from pdf_toolkit import pages
from pdf_toolkit.errors import InvalidPageRangeError


def test_parse_page_ranges_mixed():
    assert pages.parse_page_ranges("1-3,5,8-10", page_count=10) == [0, 1, 2, 4, 7, 8, 9]


def test_parse_page_ranges_deduplicates_preserving_first_occurrence():
    assert pages.parse_page_ranges("1,1-3", page_count=5) == [0, 1, 2]


def test_parse_page_ranges_reverse_range():
    assert pages.parse_page_ranges("3-1", page_count=5) == [2, 1, 0]


def test_parse_page_ranges_out_of_bounds_raises():
    with pytest.raises(InvalidPageRangeError):
        pages.parse_page_ranges("1-5", page_count=3)


def test_parse_page_ranges_empty_raises():
    with pytest.raises(InvalidPageRangeError):
        pages.parse_page_ranges("", page_count=3)


def test_parse_page_ranges_garbage_raises():
    with pytest.raises(InvalidPageRangeError):
        pages.parse_page_ranges("abc", page_count=3)


def test_reorder_pages(pdf_factory):
    doc = pdf_factory(3, label_prefix="P")
    reordered = pages.reorder_pages(doc, [2, 0, 1])
    reader = PdfReader(io.BytesIO(reordered))
    texts = [p.extract_text() for p in reader.pages]
    assert "P 3" in texts[0]
    assert "P 1" in texts[1]
    assert "P 2" in texts[2]


def test_delete_pages(pdf_factory):
    doc = pdf_factory(4)
    result = pages.delete_pages(doc, [1, 2])
    assert pages.page_count(result) == 2


def test_extract_pages(pdf_factory):
    doc = pdf_factory(5, label_prefix="X")
    result = pages.extract_pages(doc, [0, 4])
    reader = PdfReader(io.BytesIO(result))
    assert len(reader.pages) == 2
    assert "X 1" in reader.pages[0].extract_text()
    assert "X 5" in reader.pages[1].extract_text()


def test_rotate_all_pages(pdf_factory):
    doc = pdf_factory(2)
    result = pages.rotate_pages(doc, 90)
    reader = PdfReader(io.BytesIO(result))
    assert all(p.rotation == 90 for p in reader.pages)


def test_rotate_specific_page_only(pdf_factory):
    doc = pdf_factory(3)
    result = pages.rotate_pages(doc, 180, pages=[1])
    reader = PdfReader(io.BytesIO(result))
    assert [p.rotation for p in reader.pages] == [0, 180, 0]


def test_rotate_rejects_non_multiple_of_90(pdf_factory):
    doc = pdf_factory(1)
    with pytest.raises(InvalidPageRangeError):
        pages.rotate_pages(doc, 45)


def test_split_every_n(pdf_factory):
    doc = pdf_factory(5)
    chunks = pages.split_every_n(doc, 2)
    assert [pages.page_count(c) for c in chunks] == [2, 2, 1]


def test_split_by_ranges(pdf_factory):
    doc = pdf_factory(6)
    chunks = pages.split_by_ranges(doc, [[0, 1], [2, 3, 4, 5]])
    assert [pages.page_count(c) for c in chunks] == [2, 4]
