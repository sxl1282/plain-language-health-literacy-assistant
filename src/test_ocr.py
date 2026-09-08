import pytest


@pytest.mark.skip(reason="Slow PaddleOCR integration test; run manually before demo")
def test_sample_image_contains_discharge_heading():
    from src.ocr import extract_text_from_image

    text = extract_text_from_image("data/test_images/sample_discharge_summary.png")
    assert "DISCHARGE" in text.upper()
