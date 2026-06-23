from __future__ import annotations

import io

import img2pdf
import pypdfium2 as pdfium

from pdf_toolkit.errors import NoFilesProvidedError


def images_to_pdf(image_contents: list[bytes]) -> bytes:
    """Combine one or more images (jpg/png/etc.) into a single PDF, one per page."""
    if not image_contents:
        raise NoFilesProvidedError("Provide at least one image.")
    return img2pdf.convert(image_contents)


def pdf_to_images(input_bytes: bytes, *, dpi: int = 150, fmt: str = "png") -> list[bytes]:
    """Render every page of a PDF to a raster image. fmt: 'png' or 'jpeg'."""
    fmt = fmt.lower()
    pil_format = "JPEG" if fmt in ("jpg", "jpeg") else "PNG"
    scale = dpi / 72.0

    pdf = pdfium.PdfDocument(input_bytes)
    images = []
    try:
        for page in pdf:
            bitmap = page.render(scale=scale)
            pil_image = bitmap.to_pil()
            buffer = io.BytesIO()
            if pil_format == "JPEG":
                pil_image = pil_image.convert("RGB")
            pil_image.save(buffer, format=pil_format)
            images.append(buffer.getvalue())
    finally:
        pdf.close()
    return images
