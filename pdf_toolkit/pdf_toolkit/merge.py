from __future__ import annotations

import io

from pypdf import PdfReader, PdfWriter

from pdf_toolkit.errors import NoFilesProvidedError


def merge_pdfs(file_contents: list[bytes]) -> bytes:
    """Merge PDFs in the given order into a single document."""
    if not file_contents:
        raise NoFilesProvidedError("Provide at least one PDF to merge.")

    writer = PdfWriter()
    for content in file_contents:
        reader = PdfReader(io.BytesIO(content))
        for page in reader.pages:
            writer.add_page(page)

    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()
