from __future__ import annotations

import io

from pypdf import PdfReader, PdfWriter

from pdf_toolkit.errors import InvalidPageRangeError


def parse_page_ranges(spec: str, page_count: int) -> list[int]:
    """Parse a 1-indexed, human-written page range like "1-3,5,8-10" into a
    0-indexed, de-duplicated, order-preserving list of page indices."""
    spec = spec.strip()
    if not spec:
        raise InvalidPageRangeError("Page range is empty.")

    indices: list[int] = []
    seen: set[int] = set()
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start_s, _, end_s = chunk.partition("-")
            start, end = _to_int(start_s, spec), _to_int(end_s, spec)
            step = 1 if end >= start else -1
            page_numbers = range(start, end + step, step)
        else:
            page_numbers = [_to_int(chunk, spec)]
        for n in page_numbers:
            if not (1 <= n <= page_count):
                raise InvalidPageRangeError(
                    f"Page {n} is out of range for a {page_count}-page document."
                )
            idx = n - 1
            if idx not in seen:
                seen.add(idx)
                indices.append(idx)

    if not indices:
        raise InvalidPageRangeError("Page range is empty.")
    return indices


def _to_int(token: str, original_spec: str) -> int:
    token = token.strip()
    if not token.isdigit():
        raise InvalidPageRangeError(f"Invalid page range: '{original_spec}'")
    return int(token)


def reorder_pages(input_bytes: bytes, new_order: list[int]) -> bytes:
    """new_order is a 0-indexed permutation (and/or subset) of the original pages,
    in the order they should appear in the output."""
    reader = PdfReader(io.BytesIO(input_bytes))
    writer = PdfWriter()
    for idx in new_order:
        writer.add_page(reader.pages[idx])
    return _write(writer)


def delete_pages(input_bytes: bytes, pages_to_delete: list[int]) -> bytes:
    reader = PdfReader(io.BytesIO(input_bytes))
    to_delete = set(pages_to_delete)
    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i not in to_delete:
            writer.add_page(page)
    return _write(writer)


def extract_pages(input_bytes: bytes, pages: list[int]) -> bytes:
    return reorder_pages(input_bytes, pages)


def rotate_pages(input_bytes: bytes, degrees: int, pages: list[int] | None = None) -> bytes:
    """degrees must be a multiple of 90 (positive = clockwise). pages=None rotates all."""
    if degrees % 90 != 0:
        raise InvalidPageRangeError("Rotation must be a multiple of 90 degrees.")
    reader = PdfReader(io.BytesIO(input_bytes))
    target = set(pages) if pages is not None else None
    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if target is None or i in target:
            page.rotate(degrees)
        writer.add_page(page)
    return _write(writer)


def split_every_n(input_bytes: bytes, n: int) -> list[bytes]:
    if n < 1:
        raise InvalidPageRangeError("Pages per file must be at least 1.")
    reader = PdfReader(io.BytesIO(input_bytes))
    page_count = len(reader.pages)
    chunks = []
    for start in range(0, page_count, n):
        chunks.append(extract_pages(input_bytes, list(range(start, min(start + n, page_count)))))
    return chunks


def split_by_ranges(input_bytes: bytes, ranges: list[list[int]]) -> list[bytes]:
    return [extract_pages(input_bytes, r) for r in ranges]


def page_count(input_bytes: bytes) -> int:
    return len(PdfReader(io.BytesIO(input_bytes)).pages)


def _write(writer: PdfWriter) -> bytes:
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()
