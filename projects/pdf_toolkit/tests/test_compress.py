from pdf_toolkit import compress


def test_compress_fixed_quality_returns_smaller_or_equal(pdf_with_image_factory):
    doc = pdf_with_image_factory()
    result = compress.compress(doc, quality=40)
    assert result.met_target is True
    assert result.quality_used == 40
    assert result.compressed_bytes <= result.original_bytes


def test_compress_with_target_meets_target_when_possible(pdf_with_image_factory):
    doc = pdf_with_image_factory()
    target = len(doc) // 2
    result = compress.compress(doc, target_bytes=target)
    assert result.compressed_bytes <= target
    assert result.met_target is True


def test_compress_with_unreachable_target_reports_not_met(pdf_with_image_factory):
    doc = pdf_with_image_factory()
    result = compress.compress(doc, target_bytes=1)
    assert result.met_target is False
    assert result.compressed_bytes > 0


def test_compress_result_ratio(pdf_with_image_factory):
    doc = pdf_with_image_factory()
    result = compress.compress(doc, quality=30)
    assert 0 <= result.ratio <= 1
