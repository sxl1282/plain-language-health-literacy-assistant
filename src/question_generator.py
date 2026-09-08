"""
Rule-based question generation module.

This module generates patient-facing "Questions to Ask Doctor"
from English discharge summaries.

The question categories are informed by AHRQ discharge communication
resources: diagnosis / medical problem, medicines, tests and results,
follow-up appointments, and warning signs.

The module does not diagnose, interpret test results, or recommend treatment.
It only generates safe questions that patients can ask a clinician.
"""

import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))


CATEGORY_ORDER = [
    "diagnosis",
    "medication",
    "tests_results",
    "follow_up",
    "warning_signs",
]


CATEGORY_PATTERNS = {
    "diagnosis": [
        r"\bdiagnosis\b",
        r"\bdiagnoses\b",
        r"\bdiagnosed\b",
        r"\bmedical problem\b",
        r"\bcondition\b",
        r"\bproblem list\b",
    ],
    "medication": [
        r"\bmedication\b",
        r"\bmedications\b",
        r"\bmedicine\b",
        r"\bmedicines\b",
        r"\bprescription\b",
        r"\bdose\b",
        r"\bdosage\b",
        r"\btablet\b",
        r"\bcapsule\b",
        r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|unit|units)\b",
        r"\bonce daily\b",
        r"\btwice daily\b",
        r"\bdaily\b",
    ],
    "tests_results": [
        r"\btest\b",
        r"\btests\b",
        r"\blab\b",
        r"\blabs\b",
        r"\blaboratory\b",
        r"\bresult\b",
        r"\bresults\b",
        r"\bpending\b",
        r"\bct scan\b",
        r"\bct\b",
        r"\bmri\b",
        r"\bx[- ]?ray\b",
        r"\bultrasound\b",
        r"\bscan\b",
        r"\bimaging\b",
        r"\bradiology\b",
    ],
    "follow_up": [
        r"\bfollow[- ]?up\b",
        r"\bappointment\b",
        r"\bappointments\b",
        r"\bclinic\b",
        r"\bspecialist\b",
        r"\bprimary care\b",
        r"\bpcp\b",
        r"\breturn in\b",
        r"\breview in\b",
    ],
    "warning_signs": [
        r"\bsymptom\b",
        r"\bsymptoms\b",
        r"\bworse\b",
        r"\bworsening\b",
        r"\bside effect\b",
        r"\bside effects\b",
        r"\bemergency\b",
        r"\bseek medical help\b",
        r"\bcall the doctor\b",
        r"\badmitted with\b",
        r"\bpresented with\b",
        r"\bcomplained of\b",
        r"\bpain\b",
        r"\bfever\b",
        r"\bshortness of breath\b",
    ],
}


SECTION_HEADINGS = {
    "DISCHARGE SUMMARY",
    "DISCHARGE DIAGNOSES",
    "DIAGNOSES",
    "DIAGNOSIS",
    "PRIMARY DIAGNOSIS",
    "FINAL DIAGNOSIS",
    "SECONDARY DIAGNOSES",
    "HOSPITAL COURSE",
    "DISPOSITION",
    "DISCHARGE MEDICATIONS",
    "MEDICATIONS",
    "NEW MEDICATIONS",
    "PENDING RESULTS AND FOLLOW UP",
    "PENDING RESULTS AND FOLLOW-UP",
    "FOLLOW UP",
    "FOLLOW-UP",
    "PAST MEDICAL HISTORY",
    "PHYSICAL EXAMINATION",
    "LABORATORY DATA",
}


DIAGNOSIS_HEADINGS = {
    "DISCHARGE DIAGNOSES",
    "DIAGNOSES",
    "DIAGNOSIS",
    "PRIMARY DIAGNOSIS",
    "FINAL DIAGNOSIS",
    "SECONDARY DIAGNOSES",
}


IGNORE_FOLLOWUP_TARGETS = {
    "pending results and follow up",
    "pending results and follow-up",
    "follow up",
    "follow-up",
}


TEST_TERMS = [
    "ct",
    "ct scan",
    "mri",
    "x-ray",
    "xray",
    "ultrasound",
    "scan",
    "imaging",
    "radiology",
    "test",
    "lab",
]


def normalize_heading(text):
    """
    Normalize text for heading comparison.
    """

    if not text:
        return ""

    text = re.sub(r"\s+", " ", str(text)).strip()
    text = text.strip(" :;,.")
    return text.upper()


def is_section_heading(text):
    """
    Check whether a sentence-like unit is a section heading.
    """

    return normalize_heading(text) in SECTION_HEADINGS


def split_sentences(text):
    """
    Split discharge summary text into sentence-like units.
    """

    if not text:
        return []

    lines = [
        re.sub(r"\s+", " ", line).strip()
        for line in text.splitlines()
        if line.strip()
    ]

    merged_lines = []
    pending_heading = ""

    for line in lines:

        if pending_heading:
            line = pending_heading + " " + line
            pending_heading = ""

        if line.endswith(":") and len(line.split()) <= 5:
            pending_heading = line
        else:
            merged_lines.append(line)

    if pending_heading:
        merged_lines.append(pending_heading)

    sentences = []

    for line in merged_lines:

        parts = re.split(r"(?<=[.!?])\s+", line)

        for part in parts:

            part = part.strip()

            if part:
                sentences.append(part)

    return sentences


def contains_category(sentence, category):
    """
    Check whether a sentence matches a question category.
    """

    patterns = CATEGORY_PATTERNS.get(category, [])

    return any(
        re.search(pattern, sentence, flags=re.IGNORECASE)
        for pattern in patterns
    )


def build_term_pattern(term):
    """
    Build a safe matching pattern for a detected medical term.
    """

    return r"(?<![A-Za-z0-9])" + re.escape(term) + r"(?![A-Za-z0-9])"


def clean_text(value):
    """
    Clean a term or phrase before using it in a question.
    """

    if value is None:
        return ""

    value = str(value).strip()
    value = re.sub(r"\s+", " ", value)
    value = value.strip(" ,;:.()[]{}")

    if len(value) > 80:
        return ""

    return value


def find_terms_in_sentence(sentence, medical_terms):
    """
    Find detected medical terms that appear in one sentence.
    """

    found_terms = []

    for item in medical_terms:

        term = clean_text(item.get("term"))
        matched_text = clean_text(item.get("matched_text")) or term

        if not term:
            continue

        pattern = build_term_pattern(term)
        match = re.search(pattern, sentence, flags=re.IGNORECASE)

        if match:
            found_terms.append(
                {
                    "term": term,
                    "matched_text": matched_text,
                    "start": match.start(),
                    "end": match.end(),
                }
            )

    return sorted(
        found_terms,
        key=lambda x: x["start"],
    )


def is_test_term(term):
    """
    Check whether a term is related to tests or results.
    """

    term = clean_text(term).lower()

    if not term:
        return False

    return any(
        test_word in term
        for test_word in TEST_TERMS
    )


def choose_anchor(terms, exclude_tests=False):
    """
    Choose a detected term to include in a question.
    """

    for item in terms:

        anchor = clean_text(item["matched_text"])

        if not anchor:
            continue

        if exclude_tests and is_test_term(anchor):
            continue

        return anchor

    return ""


def choose_test_anchor(terms):
    """
    Choose a test-related term from detected terms.
    """

    for item in terms:

        anchor = clean_text(item["matched_text"])

        if is_test_term(anchor):
            return anchor

    return ""


def choose_medication_anchor(sentence, terms):
    """
    Choose a likely medicine name from a medication sentence.
    """

    label_match = re.search(
        r"\b(?:medication|medications|medicine|medicines|prescription|prescriptions)"
        r"(?:\s+on\s+discharge)?\s*:\s*",
        sentence,
        flags=re.IGNORECASE,
    )

    if label_match:

        for item in terms:

            if item["start"] >= label_match.end():
                return clean_text(item["matched_text"])

    dose_match = re.search(
        r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|unit|units)\b",
        sentence,
        flags=re.IGNORECASE,
    )

    if dose_match and terms:

        closest_term = min(
            terms,
            key=lambda item: abs(item["end"] - dose_match.start()),
        )

        if abs(closest_term["end"] - dose_match.start()) <= 50:
            return clean_text(closest_term["matched_text"])

    if len(terms) == 1:
        return clean_text(terms[0]["matched_text"])

    return ""


def remove_timing_from_followup_target(target):
    """
    Remove simple timing phrases from a follow-up target.
    """

    target = re.sub(
        r"\b(in|within)\s+\d+\s+"
        r"(day|days|week|weeks|month|months)\b.*$",
        "",
        target,
        flags=re.IGNORECASE,
    )

    target = re.sub(
        r"\bas scheduled\b.*$",
        "",
        target,
        flags=re.IGNORECASE,
    )

    return target.strip()


def clean_follow_up_target(sentence):
    """
    Extract a simple follow-up target from a follow-up sentence.

    Section headings such as "PENDING RESULTS AND FOLLOW UP" are ignored.
    """

    if is_section_heading(sentence):
        return ""

    sentence = clean_text(sentence)

    if not sentence:
        return ""

    if sentence.lower() in IGNORE_FOLLOWUP_TARGETS:
        return ""

    target = ""

    patterns = [
        r"(?:the\s+patient\s+will\s+)?follow[- ]?up\s+with\s+(.+)$",
        r"(?:please\s+)?follow[- ]?up\s+with\s+(.+)$",
        r"follow[- ]?up\s+appointment\s+with\s+(.+)$",
        r"appointment\s+with\s+(.+)$",
        r"seen\s+in\s+(.+)$",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            sentence,
            flags=re.IGNORECASE,
        )

        if match:
            target = match.group(1)
            break

    if not target:
        return ""

    target = remove_timing_from_followup_target(target)
    target = clean_text(target)

    if not target:
        return ""

    if target.lower() in IGNORE_FOLLOWUP_TARGETS:
        return ""

    if is_section_heading(target):
        return ""

    if len(target.split()) > 8:
        return ""

    if target.lower().startswith("the "):
        return target

    if target.lower().endswith("clinic"):
        return "the " + target

    return target


def add_unique_question(questions, question):
    """
    Add a question only once.
    """

    if question not in questions:
        questions.append(question)


def generate_questions(text, medical_terms, max_questions=6):
    """
    Generate patient-facing questions from a discharge summary.
    """

    sentences = split_sentences(text)
    candidates = {category: [] for category in CATEGORY_ORDER}

    for sentence in sentences:

        sentence_heading = normalize_heading(sentence)

        if is_section_heading(sentence):

            if sentence_heading in DIAGNOSIS_HEADINGS:
                candidates["diagnosis"].append(
                    "What is my main medical problem?"
                )

            continue

        terms = find_terms_in_sentence(sentence, medical_terms)

        if contains_category(sentence, "diagnosis"):

            anchor = choose_anchor(terms, exclude_tests=True)

            if anchor:
                question = f"What is {anchor}, and what does it mean for me?"
            else:
                question = "What is my main medical problem?"

            candidates["diagnosis"].append(question)

        if contains_category(sentence, "medication"):

            anchor = choose_medication_anchor(sentence, terms)

            if anchor:
                question = (
                    f"What is {anchor} for, how much should I take, "
                    "and how and when should I take it?"
                )
            else:
                question = (
                    "What is this medicine for, how much should I take, "
                    "and how and when should I take it?"
                )

            candidates["medication"].append(question)

        if contains_category(sentence, "tests_results"):

            anchor = choose_test_anchor(terms)
            pending = re.search(r"\bpending\b", sentence, flags=re.IGNORECASE)

            if pending:

                if anchor:
                    question = (
                        f"When will the {anchor} result be ready, "
                        "and who will discuss it with me?"
                    )
                else:
                    question = (
                        "When will these test results be ready, "
                        "and who will discuss them with me?"
                    )

            else:

                if anchor:
                    question = (
                        f"What did the {anchor} show, "
                        "and is any follow-up needed?"
                    )
                else:
                    question = (
                        "What do these test results mean, "
                        "and is any follow-up needed?"
                    )

            candidates["tests_results"].append(question)

        if contains_category(sentence, "follow_up"):

            target = clean_follow_up_target(sentence)

            if target:
                question = (
                    f"When and where should I follow up with {target}, "
                    "and what is it for?"
                )
            else:
                question = (
                    "When and where is my next follow-up appointment, "
                    "and what is it for?"
                )

            candidates["follow_up"].append(question)

        if contains_category(sentence, "warning_signs"):

            anchor = choose_anchor(terms, exclude_tests=True)

            if anchor:
                question = (
                    f"What changes related to {anchor} mean I should call a doctor, "
                    "and what should I do in an emergency?"
                )
            else:
                question = (
                    "What changes mean I should call a doctor, "
                    "and what should I do in an emergency?"
                )

            candidates["warning_signs"].append(question)

    questions = []

    for category in CATEGORY_ORDER:

        if len(questions) >= max_questions:
            break

        if candidates[category]:
            add_unique_question(
                questions,
                candidates[category][0],
            )

    fallback_questions = [
        "What do I need to do after I leave the hospital?",
        "Why is this after-hospital plan important?",
        "Which medicines should I take, and how much, how, and when should I take them?",
        "What follow-up appointments or tests do I need after discharge?",
        "Are any test results still pending, and who will discuss them with me?",
        "Who should I call if I feel worse or have a problem?",
    ]

    for question in fallback_questions:

        if len(questions) >= max_questions:
            break

        add_unique_question(
            questions,
            question,
        )

    return questions[:max_questions]


if __name__ == "__main__":

    from src.simplifier import simplify_medical_text

    test_text = """
    DISCHARGE SUMMARY

    Patient Name: Sample Patient

    DISCHARGE DIAGNOSES

    1. Hypertension.
    2. Chest pain.

    DISCHARGE MEDICATIONS

    1. Amlodipine 5 mg once daily.

    PENDING RESULTS AND FOLLOW UP

    Follow-up with cardiology clinic.
    CT scan was performed and the result is pending.
    """

    result = simplify_medical_text(
        test_text,
        glossary_version="filtered",
    )

    questions = generate_questions(
        test_text,
        result["medical_terms"],
    )

    print("Generated Questions:")

    for question in questions:
        print("-", question)