"""Best-effort masking for text sent to the optional Llama service."""

import re


LABEL_PATTERNS = {
    "PATIENT_NAME": r"patient\s+name|name",
    "DATE_OF_BIRTH": r"date\s+of\s+birth|dob|d\.o\.b\.",
    "PATIENT_ID": r"mrn|medical\s+record\s+number|nhs\s+number|patient\s+id",
    "ADDRESS": r"address",
    "PHONE": r"phone|telephone|mobile",
    "EMAIL": r"e-?mail",
}


def mask_identifiers(text):
    """Replace common identifiers while leaving clinical content intact.

    This is a prototype safeguard, not complete anonymisation.
    """
    if not text:
        return ""

    masked = str(text)

    for placeholder, label_pattern in LABEL_PATTERNS.items():
        masked = re.sub(
            rf"(?im)^(\s*(?:{label_pattern})\s*:)\s*[^\r\n]+",
            rf"\1 [{placeholder}]",
            masked,
        )

    masked = re.sub(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        "[EMAIL]",
        masked,
        flags=re.IGNORECASE,
    )
    masked = re.sub(
        r"(?<!\w)(?:\+?\d[\d ()-]{7,}\d)(?!\w)",
        "[PHONE_OR_ID]",
        masked,
    )
    masked = re.sub(
        r"\b(?:\d{1,2}[/-]){2}\d{2,4}\b|"
        r"\b\d{4}-\d{1,2}-\d{1,2}\b|"
        r"\b\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|"
        r"May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
        r"Nov(?:ember)?|Dec(?:ember)?)\s+\d{2,4}\b",
        "[DATE]",
        masked,
        flags=re.IGNORECASE,
    )

    return masked
