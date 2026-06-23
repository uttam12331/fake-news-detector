from pdf_toolkit import compress, convert, merge, pages, protect, watermark
from pdf_toolkit.compress import CompressResult
from pdf_toolkit.errors import (
    IncorrectPasswordError,
    InvalidPageRangeError,
    NoFilesProvidedError,
    PdfToolkitError,
)

__all__ = [
    "merge",
    "pages",
    "protect",
    "watermark",
    "convert",
    "compress",
    "CompressResult",
    "PdfToolkitError",
    "InvalidPageRangeError",
    "IncorrectPasswordError",
    "NoFilesProvidedError",
]
