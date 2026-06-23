from __future__ import annotations

import io
from dataclasses import dataclass

import pikepdf
from PIL import Image

# (jpeg_quality, max_image_dimension_px) tiers, tried from least to most aggressive.
# max_image_dimension_px=None means "don't downscale, just recompress".
_TIERS: list[tuple[int, int | None]] = [
    (90, None),
    (80, 2200),
    (70, 1800),
    (60, 1400),
    (50, 1100),
    (40, 900),
    (30, 700),
    (20, 550),
    (10, 400),
]


@dataclass
class CompressResult:
    data: bytes
    original_bytes: int
    compressed_bytes: int
    met_target: bool
    quality_used: int

    @property
    def ratio(self) -> float:
        if self.original_bytes == 0:
            return 0.0
        return 1 - (self.compressed_bytes / self.original_bytes)


def compress(input_bytes: bytes, *, target_bytes: int | None = None, quality: int = 70) -> CompressResult:
    """Recompress every raster image embedded in the PDF.

    - target_bytes given: search from the highest-quality tier downward and return the
      first result that fits, i.e. the best quality that still meets the size target.
      If no tier reaches it, returns the smallest achieved with met_target=False.
    - target_bytes=None: a single pass at the given fixed `quality`.
    """
    original_bytes = len(input_bytes)

    if target_bytes is None:
        data = _compress_once(input_bytes, quality=quality, max_dimension=None)
        return CompressResult(data, original_bytes, len(data), met_target=True, quality_used=quality)

    best = None
    for q, max_dim in _TIERS:
        data = _compress_once(input_bytes, quality=q, max_dimension=max_dim)
        best = (data, q)
        if len(data) <= target_bytes:
            return CompressResult(data, original_bytes, len(data), met_target=True, quality_used=q)

    data, q = best
    return CompressResult(data, original_bytes, len(data), met_target=False, quality_used=q)


def _compress_once(input_bytes: bytes, *, quality: int, max_dimension: int | None) -> bytes:
    with pikepdf.open(io.BytesIO(input_bytes)) as pdf:
        for page in pdf.pages:
            for raw_image in page.get_images().values():
                _recompress_image(raw_image, quality=quality, max_dimension=max_dimension)

        out = io.BytesIO()
        pdf.save(out, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.generate)
        return out.getvalue()


def _recompress_image(raw_image: pikepdf.Object, *, quality: int, max_dimension: int | None) -> None:
    try:
        pil_image = pikepdf.PdfImage(raw_image).as_pil_image()
    except Exception:
        # Unsupported colorspace/filter (e.g. JPEG2000, indexed CMYK) -- leave it untouched
        # rather than failing the whole document over one image.
        return

    pil_image = pil_image.convert("RGB")
    if max_dimension and max(pil_image.size) > max_dimension:
        ratio = max_dimension / max(pil_image.size)
        new_size = (max(1, round(pil_image.width * ratio)), max(1, round(pil_image.height * ratio)))
        pil_image = pil_image.resize(new_size, Image.LANCZOS)

    buffer = io.BytesIO()
    pil_image.save(buffer, format="JPEG", quality=quality, optimize=True)

    try:
        raw_image.write(buffer.getvalue(), filter=pikepdf.Name("/DCTDecode"))
    except Exception:
        return
    raw_image.ColorSpace = pikepdf.Name("/DeviceRGB")
    raw_image.BitsPerComponent = 8
    raw_image.Width = pil_image.width
    raw_image.Height = pil_image.height
    if "/SMask" in raw_image:
        del raw_image.SMask
    if "/Decode" in raw_image:
        del raw_image.Decode
