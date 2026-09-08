"""
Citation module.

This module links detected medical terms back to source sentences
in the original discharge summary.

It supports sentence-level source linking for all detected terms.
"""

import re


def split_sentences_with_spans(text):
    """
    Split text into sentence-like units and keep character spans.

    The method is intentionally simple because OCR text may have imperfect
    punctuation and line breaks.
    """

    if not text:
        return []

    sentence_pattern = re.compile(
        r"[^.!?\n]+[.!?]?",
        flags=re.MULTILINE,
    )

    sentences = []

    for match in sentence_pattern.finditer(text):

        sentence_text = match.group(0).strip()

        if not sentence_text:
            continue

        sentences.append(
            {
                "text": sentence_text,
                "start": match.start(),
                "end": match.end(),
            }
        )

    return sentences


def create_marker(index):
    """
    Create a readable citation marker.

    Square brackets are used instead of circled numbers so the system can
    support more than 10 detected terms.
    """

    return f"[{index}]"


def find_source_sentence_for_term(text, term_item, sentences):
    """
    Find the source sentence that contains a detected term.

    Character-span matching is preferred because it is more reliable than
    text-only matching when OCR punctuation is messy.
    """

    term = term_item.get("term", "")
    matched_text = term_item.get("matched_text", term)
    start = term_item.get("start")
    end = term_item.get("end")

    # Prefer character-span matching.
    if isinstance(start, int) and isinstance(end, int):

        for sentence in sentences:

            if sentence["start"] <= start and end <= sentence["end"]:
                return sentence["text"]

    # Fallback: text matching.
    search_text = matched_text or term

    if not search_text:
        return ""

    pattern = (
        r"(?<![A-Za-z0-9])"
        + re.escape(search_text)
        + r"(?![A-Za-z0-9])"
    )

    for sentence in sentences:

        if re.search(pattern, sentence["text"], flags=re.IGNORECASE):
            return sentence["text"]

    # Final fallback: return a short local context around the detected span.
    if isinstance(start, int) and isinstance(end, int):

        context_start = max(0, start - 120)
        context_end = min(len(text), end + 120)

        return text[context_start:context_end].strip()

    return ""


def create_citations(text, medical_terms):
    """Create one citation per term and retain every matching sentence."""

    sentences = split_sentences_with_spans(text)

    citations = []

    for index, item in enumerate(medical_terms, start=1):

        term = item.get("term", "")
        matched_text = item.get("matched_text", term)
        explanation = item.get("explanation", "")

        search_text = matched_text or term
        pattern = (
            r"(?<![A-Za-z0-9])"
            + re.escape(search_text)
            + r"(?![A-Za-z0-9])"
        )
        source_sentences = [
            sentence["text"]
            for sentence in sentences
            if re.search(pattern, sentence["text"], flags=re.IGNORECASE)
        ]

        if not source_sentences:
            fallback = find_source_sentence_for_term(text, item, sentences)
            source_sentences = [fallback] if fallback else []

        citations.append(
            {
                "marker": create_marker(index),
                "term": term,
                "matched_text": matched_text,
                "explanation": explanation,
                "source": "\n".join(source_sentences),
                "source_sentences": source_sentences,
            }
        )

    return citations


def highlight_terms(text, citations):
    """
    Add citation markers after detected terms in the original text.

    Longer terms are processed first to avoid partial phrase matching.
    """

    highlighted_text = text

    sorted_citations = sorted(
        citations,
        key=lambda item: len(item.get("matched_text", item.get("term", ""))),
        reverse=True,
    )

    for item in sorted_citations:

        matched_text = item.get("matched_text", item.get("term", ""))
        marker = item.get("marker", "")

        if not matched_text or not marker:
            continue

        pattern = (
            r"(?<![A-Za-z0-9])"
            + re.escape(matched_text)
            + r"(?![A-Za-z0-9])"
        )

        highlighted_text = re.sub(
            pattern,
            rf"\g<0>{marker}",
            highlighted_text,
            flags=re.IGNORECASE,
        )

    return highlighted_text


if __name__ == "__main__":
    sample_text = """
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
            "matched_text": "Hypertension",
            "explanation": "High blood pressure.",
            "start": 58,
            "end": 70,
        },
    ]

    citations = create_citations(sample_text, sample_terms)

    print("Citations:")
    for item in citations:
        print(item)

    print("\nHighlighted Text:")
    print(highlight_terms(sample_text, citations))
