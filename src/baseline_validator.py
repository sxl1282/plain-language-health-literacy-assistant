"""Internal consistency warnings for term detection and source linking."""

import re


def normalize_text(text):
    """
    Normalize text for simple matching.
    """
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def contains_term(text, term):
    """
    Check whether a term appears in text with simple word boundaries.
    """
    pattern = r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])"
    return re.search(pattern, text, flags=re.IGNORECASE) is not None


def find_citation_for_term(term, citations):
    """
    Find the citation entry for a detected medical term.
    """
    for citation in citations:
        if citation.get("term", "").lower() == term.lower():
            return citation

    return None


def validate_detected_term(original_text, term_item, citations):
    """
    Validate one detected medical term.
    """
    warnings = []

    term = term_item.get("term", "").strip()
    matched_text = term_item.get("matched_text", "").strip()
    explanation = term_item.get("explanation", "").strip()
    start = term_item.get("start")
    end = term_item.get("end")

    if not term:
        warnings.append(
            {
                "category": "missing_term",
                "term": term,
                "message": "A detected term entry is missing the term value.",
            }
        )
        return warnings

    if not explanation:
        warnings.append(
            {
                "category": "missing_explanation",
                "term": term,
                "message": "The detected term does not have a plain-language explanation.",
            }
        )

    if not contains_term(original_text, matched_text or term):
        warnings.append(
            {
                "category": "term_not_found_in_source",
                "term": term,
                "message": "The detected term or matched text was not found in the original source text.",
            }
        )

    if isinstance(start, int) and isinstance(end, int):
        if start < 0 or end > len(original_text) or start >= end:
            warnings.append(
                {
                    "category": "invalid_span",
                    "term": term,
                    "message": "The detected term has an invalid character span.",
                }
            )
        else:
            source_span = original_text[start:end]
            expected_text = matched_text or term

            if normalize_text(source_span) != normalize_text(expected_text):
                warnings.append(
                    {
                        "category": "span_mismatch",
                        "term": term,
                        "message": (
                            "The stored character span does not match the detected term text. "
                            f"Expected '{expected_text}', but source span is '{source_span}'."
                        ),
                    }
                )
    else:
        warnings.append(
            {
                "category": "missing_span",
                "term": term,
                "message": "The detected term does not have valid start/end character positions.",
            }
        )

    citation = find_citation_for_term(term, citations)

    if citation is None:
        warnings.append(
            {
                "category": "missing_source_sentence",
                "term": term,
                "message": "No source sentence citation was found for this detected term.",
            }
        )
    else:
        source_sentence = citation.get("source", "")

        if not source_sentence:
            warnings.append(
                {
                    "category": "empty_source_sentence",
                    "term": term,
                    "message": "The citation source sentence is empty.",
                }
            )
        elif not contains_term(source_sentence, matched_text or term):
            warnings.append(
                {
                    "category": "source_sentence_mismatch",
                    "term": term,
                    "message": "The linked source sentence does not contain the detected term.",
                }
            )

    return warnings


def validate_baseline_output(
    original_text,
    medical_terms,
    citations,
    patient_friendly_version="",
    max_terms_without_warning=40,
):
    """
    Validate the rule-based baseline output.

    Args:
        original_text (str): Original discharge summary text.
        medical_terms (list): Detected medical terms.
        citations (list): Source sentence citations.
        patient_friendly_version (str): Rule-based patient-friendly version.
        max_terms_without_warning (int): Threshold for over-detection warning.

    Returns:
        dict: Validation result with status and warning list.
    """
    warnings = []

    if not original_text or not original_text.strip():
        return {
            "status": "not_run",
            "warning_count": 0,
            "warnings": [],
            "summary": "Original text is empty, so baseline validation was not run.",
        }

    if not medical_terms:
        return {
            "status": "warning",
            "warning_count": 1,
            "warnings": [
                {
                    "category": "no_terms_detected",
                    "term": "",
                    "message": (
                        "No medical terms were detected. This may be correct for simple text, "
                        "but should be manually checked for discharge summaries."
                    ),
                }
            ],
            "summary": "No medical terms were detected by the rule-based baseline.",
        }

    if len(medical_terms) > max_terms_without_warning:
        warnings.append(
            {
                "category": "possible_over_detection",
                "term": "",
                "message": (
                    f"{len(medical_terms)} medical terms were detected. "
                    "This may indicate over-detection or over-replacement risk in long OCR text."
                ),
            }
        )

    seen_terms = set()

    for term_item in medical_terms:
        term = term_item.get("term", "").strip().lower()

        if term in seen_terms:
            warnings.append(
                {
                    "category": "duplicate_detected_term",
                    "term": term,
                    "message": "The same medical term appears more than once in the detected term list.",
                }
            )

        seen_terms.add(term)

        term_warnings = validate_detected_term(
            original_text=original_text,
            term_item=term_item,
            citations=citations,
        )

        warnings.extend(term_warnings)

    if not patient_friendly_version or not patient_friendly_version.strip():
        warnings.append(
            {
                "category": "missing_patient_friendly_version",
                "term": "",
                "message": "The rule-based Patient-Friendly Version is empty.",
            }
        )

    if warnings:
        return {
            "status": "warning",
            "warning_count": len(warnings),
            "warnings": warnings,
            "summary": (
                "Potential rule-based baseline issues were flagged. "
                "These warnings should be manually checked against the original discharge summary."
            ),
        }

    return {
        "status": "pass",
        "warning_count": 0,
        "warnings": [],
        "summary": (
            "No configured internal consistency warning patterns were detected. "
            "This does not establish clinical correctness."
        ),
    }


def format_baseline_validator_result(validation_result):
    """
    Convert baseline validation result into readable text for terminal testing.
    """
    lines = []

    lines.append("Rule-based Baseline Validator Result")
    lines.append("=" * 40)
    lines.append(f"Status: {validation_result['status']}")
    lines.append(f"Warning count: {validation_result['warning_count']}")
    lines.append(f"Summary: {validation_result['summary']}")

    if validation_result["warnings"]:
        lines.append("")
        lines.append("Warnings:")

        for index, warning in enumerate(validation_result["warnings"], start=1):
            lines.append(f"{index}. Category: {warning['category']}")
            lines.append(f"   Term: {warning.get('term', '')}")
            lines.append(f"   Message: {warning['message']}")

    return "\n".join(lines)


if __name__ == "__main__":
    sample_original = """
    The patient was admitted with chest pain.
    Diagnosis: Hypertension.
    Medication: Amlodipine 5 mg once daily.
    """

    sample_terms = [
        {
            "term": "chest pain",
            "matched_text": "chest pain",
            "explanation": "Feeling of discomfort in the chest area.",
            "start": 35,
            "end": 45,
        },
        {
            "term": "hypertension",
            "matched_text": "hypertension",
            "explanation": "",
            "start": 58,
            "end": 70,
        },
    ]

    sample_citations = [
        {
            "marker": "①",
            "term": "chest pain",
            "explanation": "Feeling of discomfort in the chest area.",
            "source": "The patient was admitted with chest pain.",
        }
    ]

    sample_patient_friendly_version = """
    The patient was admitted with chest pain.
    The main diagnosis was high blood pressure.
    """

    result = validate_baseline_output(
        original_text=sample_original,
        medical_terms=sample_terms,
        citations=sample_citations,
        patient_friendly_version=sample_patient_friendly_version,
    )

    print(format_baseline_validator_result(result))
