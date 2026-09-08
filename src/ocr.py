"""
OCR module for extracting text from medical document images.

This module uses PaddleOCR to extract text from uploaded medical document images.
"""

from paddleocr import PaddleOCR


# Initialise PaddleOCR once
ocr_model = PaddleOCR(use_angle_cls=True, lang="en")


def extract_text_from_image(image_path):
    """
    Extract text from an image file using PaddleOCR.

    Args:
        image_path (str): Path to the input image.

    Returns:
        str: Extracted text from the image.
    """
    result = ocr_model.ocr(image_path)

    extracted_lines = []

    for page in result:
        if "rec_texts" in page:
            extracted_lines.extend(page["rec_texts"])

    return "\n".join(extracted_lines)