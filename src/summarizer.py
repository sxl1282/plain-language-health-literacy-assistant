"""
Patient-friendly rewriting module.

This module creates a simple rule-based patient-friendly version of a
discharge summary using the filtered patient-facing glossary.

It is used as a transparent baseline, so the output is intentionally simple.
"""

import re


def build_term_pattern(term):
    """
    Build a safe matching pattern for a medical term.
    """
    return r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])"


def normalize_spaces(text):
    """
    Remove repeated spaces.
    """
    return re.sub(r"\s+", " ", text).strip()


def lowercase_first(text):
    """
    Lowercase the first character.
    """
    text = text.strip()

    if not text:
        return text

    return text[0].lower() + text[1:]


def capitalize_first(text):
    """
    Capitalize the first character.
    """
    text = text.strip()

    if not text:
        return text

    return text[0].upper() + text[1:]


def ensure_period(text):
    """
    Add a period if needed.
    """
    text = text.strip()

    if not text:
        return text

    if text[-1] in ".!?":
        return text

    return text + "."


def shorten_explanation(term, explanation):
    """
    Convert glossary explanation into a shorter phrase.
    """

    if not explanation:
        return ""

    term = term.lower().strip()

    explanation = (
        explanation
        .strip()
        .rstrip(".")
    )

    if ":" in explanation:
        explanation = explanation.split(":")[0]

    explanation = re.split(
        r"[.!?]",
        explanation
    )[0].strip()

    definition_patterns = [
        rf"^(a|an|the)?\s*{re.escape(term)}\s+"
        r"(is|are|means|refers to|describes)\s+",

        r"^(a|an|the)?\s*medical term for\s+",

        r"^(a|an|the)?\s*term used to describe\s+",

        r"^(a|an|the)?\s*term that means\s+",
    ]

    for pattern in definition_patterns:

        explanation = re.sub(
            pattern,
            "",
            explanation,
            flags=re.IGNORECASE,
        ).strip()

    explanation = re.sub(
        r"^the study of\s+",
        "",
        explanation,
        flags=re.IGNORECASE,
    )

    return normalize_spaces(explanation)


def is_medication_like_term(item):
    """
    Check whether a detected term appears to be a medicine name.

    Medicine names should be kept in the rewritten text because patients
    need the exact medication name and dose.
    """

    explanation = item.get("explanation", "").lower()

    medication_clues = [
        "medication",
        "medicine",
        "drug",
        "antibiotic",
        "steroid",
        "helps improve blood flow",
        "decrease blood pressure",
        "lowers blood pressure",
        "lowers the body's immune response",
    ]

    return any(
        clue in explanation
        for clue in medication_clues
    )


def get_terms_in_sentence(sentence, medical_terms):
    """
    Find medical terms appearing in a sentence.
    """

    found = []

    for item in medical_terms:

        term = item["term"]

        if re.search(
            build_term_pattern(term),
            sentence,
            flags=re.IGNORECASE,
        ):
            found.append(item)

    return sorted(
        found,
        key=lambda x: len(x["term"]),
        reverse=True,
    )


def replace_terms_in_sentence(sentence, terms):
    """
    Replace detected non-medication terms with plain-language phrases.

    Medication-like terms are not directly replaced, because replacing a
    medicine name can remove important safety information.
    """

    rewritten = sentence

    for item in terms:

        if is_medication_like_term(item):
            continue

        term = item["term"]

        phrase = shorten_explanation(
            term,
            item["explanation"],
        )

        if not phrase:
            continue

        rewritten = re.sub(
            build_term_pattern(term),
            lowercase_first(phrase),
            rewritten,
            flags=re.IGNORECASE,
        )

    return capitalize_first(
        normalize_spaces(rewritten)
    )


def format_medicine_explanation(medicine_name, plain_phrase):
    """
    Add a short explanation while keeping the medicine name.
    """

    plain_phrase = lowercase_first(plain_phrase)

    plain_phrase = re.sub(
        r"^(a|an)?\s*(medicine|medication)\s+that\s+",
        "",
        plain_phrase,
        flags=re.IGNORECASE,
    ).strip()

    plain_phrase = re.sub(
        r"^(a|an)?\s*(medicine|medication)\s+",
        "",
        plain_phrase,
        flags=re.IGNORECASE,
    ).strip()

    if plain_phrase.startswith(
        (
            "helps ",
            "improves ",
            "reduces ",
            "lowers ",
            "decreases ",
        )
    ):
        return f"{medicine_name} {plain_phrase}."

    return f"{medicine_name}: {plain_phrase}."


def rewrite_medication_sentence(sentence, terms):
    """
    Rewrite Medication: or Medications: sentences.

    This keeps medication names and doses.
    It does not infer prescribed, started, stopped, or changed status.
    """

    medication_match = re.match(
        r"^(Medication|Medications):\s*(.+)$",
        sentence,
        flags=re.IGNORECASE,
    )

    if not medication_match:
        return None

    medication_text = medication_match.group(2).strip()
    medication_text = ensure_period(medication_text)

    explanation_sentences = []

    for item in terms:

        if not is_medication_like_term(item):
            continue

        term = item["term"]

        match = re.search(
            build_term_pattern(term),
            medication_text,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        medicine_name = match.group(0)

        explanation = shorten_explanation(
            term,
            item["explanation"],
        )

        if explanation:
            explanation_sentences.append(
                format_medicine_explanation(
                    medicine_name,
                    explanation,
                )
            )

    output = (
        f"The discharge summary lists "
        f"{medication_text}"
    )

    if explanation_sentences:
        output += " " + " ".join(explanation_sentences)

    return normalize_spaces(output)


def rewrite_followup_sentence(sentence, terms):
    """
    Rewrite follow-up information.
    """

    match = re.match(
        r"^Follow-up with\s+(.+)$",
        sentence,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    followup_text = match.group(1)

    for item in terms:

        if is_medication_like_term(item):
            continue

        term = item["term"]

        explanation = shorten_explanation(
            term,
            item["explanation"],
        )

        if not explanation:
            continue

        followup_text = re.sub(
            build_term_pattern(term),
            lowercase_first(explanation),
            followup_text,
            count=1,
            flags=re.IGNORECASE,
        )

    return (
        "Follow up with "
        + normalize_spaces(followup_text)
    )


def rewrite_sentence(sentence, medical_terms):
    """
    Rewrite one sentence.
    """

    sentence = sentence.strip()

    if not sentence:
        return ""

    terms = get_terms_in_sentence(
        sentence,
        medical_terms,
    )

    if not terms:
        return sentence

    diagnosis_match = re.match(
        r"^Diagnosis:\s*(.+)$",
        sentence,
        flags=re.IGNORECASE,
    )

    if diagnosis_match:

        result = replace_terms_in_sentence(
            diagnosis_match.group(1),
            terms,
        )

        return (
            "The main diagnosis was "
            + lowercase_first(result)
        )

    medication_result = rewrite_medication_sentence(
        sentence,
        terms,
    )

    if medication_result:
        return medication_result

    followup_result = rewrite_followup_sentence(
        sentence,
        terms,
    )

    if followup_result:
        return followup_result

    admission_match = re.match(
        r"^The patient was admitted with\s+(.+)$",
        sentence,
        flags=re.IGNORECASE,
    )

    if admission_match:

        reason = replace_terms_in_sentence(
            admission_match.group(1),
            terms,
        )

        return (
            "The patient was admitted with "
            + lowercase_first(reason)
        )

    return replace_terms_in_sentence(
        sentence,
        terms,
    )


def split_sentences(text):
    """
    Split text into sentence-like units.
    """

    sentences = re.split(
        r"(?<=[.!?])\s+",
        text.strip(),
    )

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


def generate_patient_friendly_version(
    text,
    medical_terms,
):
    """
    Generate rule-based patient-friendly version.
    """

    if not text:
        return ""

    sentences = split_sentences(text)

    rewritten = [
        rewrite_sentence(
            sentence,
            medical_terms,
        )
        for sentence in sentences
    ]

    return normalize_spaces(
        " ".join(rewritten)
    )


if __name__ == "__main__":

    from simplifier import simplify_medical_text

    test_text = """
    The patient was admitted with chest pain.
    Diagnosis: Hypertension.
    Medication: Amlodipine 5mg once daily.
    Follow-up with cardiology clinic.
    """

    result = simplify_medical_text(
        test_text,
        glossary_version="filtered",
    )

    output = generate_patient_friendly_version(
        test_text,
        result["medical_terms"],
    )

    print(output)