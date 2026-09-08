"""
Medical term simplification module.

This module identifies medical jargon in discharge summaries
and provides patient-friendly explanations.

It supports two glossary versions:
1. baseline: original README glossary
2. filtered: patient-facing filtered glossary

It also applies phrase-level matching, so longer clinical phrases
such as "CT scan" are detected before shorter overlapping terms
such as "CT" or "scan".
"""

import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))


from data.processed.readme_replacements import replacements as readme_replacements
from data.processed.patient_replacements import replacements as patient_replacements


def build_term_pattern(term):
    """
    Build a safe matching pattern for medical terms.

    This prevents matching a term inside another word.
    """

    return r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])"


def get_glossary(glossary_version="filtered"):
    """
    Select which glossary to use.

    Args:
        glossary_version (str):
            "baseline" uses the original README glossary.
            "filtered" uses the patient-facing filtered glossary.

    Returns:
        dict:
            medical term -> plain-language explanation
    """

    if glossary_version == "baseline":
        return readme_replacements

    if glossary_version == "filtered":
        return patient_replacements

    raise ValueError("glossary_version must be 'baseline' or 'filtered'")


def spans_overlap(span_a, span_b):
    """
    Check whether two text spans overlap.

    Args:
        span_a (tuple): start and end position of one match
        span_b (tuple): start and end position of another match

    Returns:
        bool: True if spans overlap
    """

    start_a, end_a = span_a
    start_b, end_b = span_b

    return start_a < end_b and start_b < end_a


def extract_medical_terms(text, glossary_version="filtered"):
    """
    Identify medical jargon appearing in the document.

    Longer phrase-level matches are preferred over shorter overlapping terms.
    For example, if "CT scan" is detected, "CT" and "scan" inside the same
    phrase will not be returned again.

    Args:
        text (str):
            OCR extracted discharge summary text

        glossary_version (str):
            "baseline" or "filtered"

    Returns:
        list:
            detected medical terms with explanations and text positions
    """

    glossary = get_glossary(glossary_version)

    candidate_matches = []

    for term, explanation in glossary.items():

        clean_term = term.strip().lower()

        if not clean_term:
            continue

        pattern = build_term_pattern(clean_term)

        for match in re.finditer(pattern, text, flags=re.IGNORECASE):

            candidate_matches.append(
                {
                    "term": clean_term,
                    "matched_text": match.group(0),
                    "explanation": explanation.strip(),
                    "start": match.start(),
                    "end": match.end(),
                    "length": len(clean_term),
                }
            )

    # Match longer clinical phrases first
    candidate_matches = sorted(
        candidate_matches,
        key=lambda x: (-x["length"], x["start"])
    )

    selected_matches = []
    selected_spans = []

    for item in candidate_matches:

        current_span = (item["start"], item["end"])

        has_overlap = any(
            spans_overlap(current_span, existing_span)
            for existing_span in selected_spans
        )

        if not has_overlap:
            selected_matches.append(item)
            selected_spans.append(current_span)

    # Sort final matches by their order in the original document
    selected_matches = sorted(
        selected_matches,
        key=lambda x: x["start"]
    )

    # Avoid showing the same term multiple times in the explanation list
    final_terms = []
    seen_terms = set()

    for item in selected_matches:

        if item["term"] in seen_terms:
            continue

        final_terms.append(
            {
                "term": item["term"],
                "matched_text": item["matched_text"],
                "explanation": item["explanation"],
                "start": item["start"],
                "end": item["end"],
            }
        )

        seen_terms.add(item["term"])

    return final_terms


def simplify_medical_text(text, glossary_version="filtered"):
    """
    Main simplification function.

    Args:
        text (str):
            original discharge summary text

        glossary_version (str):
            "baseline" or "filtered"

    Returns:
        dict:
            detected medical terms and glossary version
    """

    medical_terms = extract_medical_terms(
        text,
        glossary_version=glossary_version
    )

    return {
        "medical_terms": medical_terms,
        "glossary_version": glossary_version,
    }


if __name__ == "__main__":

    test_text = """
    The patient was admitted with chest pain.
    Diagnosis: Hypertension.
    Medication: Amlodipine 5mg once daily.
    Follow-up with cardiology clinic.
    CT scan was performed.
    """

    result = simplify_medical_text(
        test_text,
        glossary_version="filtered"
    )

    print("Detected Medical Terms:")

    for item in result["medical_terms"]:
        print(
            f"- {item['term']}: {item['explanation']}"
        )

    print("\nGlossary Version:")
    print(result["glossary_version"])