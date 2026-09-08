"""
Rule-based faithfulness validator for Llama-generated patient-friendly rewrites.

This module checks whether the Llama output contains high-risk wording
that may indicate unsupported information compared with the original
discharge summary.

It is a lightweight warning system only.
It does not prove that an output is correct or incorrect.
"""

import re


RISK_PHRASE_GROUPS = {
    "unsupported_medication_or_treatment_change": {
        "description": "Possible unsupported medication or treatment action.",
        "phrases": [
            "started",
            "start taking",
            "stopped",
            "stop taking",
            "changed",
            "prescribed",
            "recommended",
            "discontinued",
            "increased",
            "decreased",
            "new medication",
            "treatment plan",
            "your doctor gave you medicine",
            "medicine to help",
        ],
    },
    "unsupported_causal_explanation": {
        "description": "Possible unsupported causal explanation.",
        "phrases": [
            "because",
            "caused by",
            "due to",
            "leading to",
            "resulting in",
            "which can cause",
            "as a result",
            "therefore",
            "can lead to",
            "led to",
            "got worse quickly",
        ],
    },
    "unsupported_test_purpose": {
        "description": "Possible unsupported test-purpose explanation.",
        "phrases": [
            "to find out why",
            "to find the cause",
            "to check whether",
            "to check if",
            "to see whether",
            "to see if",
            "to look for",
            "to help us understand",
            "understand your condition",
            "need a test",
            "need another test",
            "you'll also need a test",
            "you will also need a test",
        ],
    },
    "unsupported_advice_or_recommendation": {
        "description": "Possible unsupported advice or recommendation.",
        "phrases": [
            "you should",
            "you need to",
            "you'll need to",
            "you will need to",
            "you'll also need",
            "you will also need",
            "avoid",
            "diet",
            "lifestyle",
            "make sure to",
        ],
    },
    "unsupported_general_medical_claim": {
        "description": "Possible unsupported general medical claim.",
        "phrases": [
            "risk of",
            "heart attack",
            "stroke",
            "infection can",
            "usually means",
            "can cause problems",
            "can be a problem",
            "under control",
            "healthy",
            "blockages",
            "no blockages",
            "swelling in your lungs",
            "fluid buildup",
            "heart function",
            "to help with inflammation",
            "to help with breathing",
            "to help with allergies",
            "to help with your blood pressure",
        ],
    },
    "unsupported_follow_up_interpretation": {
        "description": "Possible unsupported follow-up interpretation.",
        "phrases": [
            "your doctor will check on you",
            "will check on you",
            "in the future to see",
            "how your lungs are doing",
        ],
    },
}


def normalize_text(text):
    """
    Normalize text for rule-based matching.
    """

    if not text:
        return ""

    text = str(text).lower()

    # Normalize common apostrophe variants.
    text = text.replace("’", "'")
    text = text.replace("‘", "'")

    # Normalize whitespace.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def split_sentences(text):
    """
    Split generated output into simple sentence-like units.
    """

    if not text:
        return []

    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


def contains_phrase(text, phrase):
    """
    Check whether a phrase appears with simple word boundaries.
    """

    normalized_text = normalize_text(text)
    normalized_phrase = normalize_text(phrase)

    if not normalized_text or not normalized_phrase:
        return False

    pattern = (
        r"(?<![a-zA-Z0-9])"
        + re.escape(normalized_phrase)
        + r"(?![a-zA-Z0-9])"
    )

    return re.search(pattern, normalized_text, flags=re.IGNORECASE) is not None


def validate_llama_output(original_text, llama_output, max_warnings=30):
    """
    Validate Llama output against the original discharge summary.

    Args:
        original_text (str): Original discharge summary text.
        llama_output (str): Llama-generated patient-friendly version.
        max_warnings (int): Maximum number of warnings to return.

    Returns:
        dict: Validation result with status and warning list.
    """

    if not llama_output or not llama_output.strip():
        return {
            "status": "not_run",
            "warning_count": 0,
            "warnings": [],
            "summary": (
                "Llama output was not generated, so faithfulness validation "
                "was not run."
            ),
        }

    normalized_original = normalize_text(original_text)
    generated_sentences = split_sentences(llama_output)

    warnings = []
    seen_warnings = set()

    for sentence in generated_sentences:
        normalized_sentence = normalize_text(sentence)

        for category, group_info in RISK_PHRASE_GROUPS.items():
            for phrase in group_info["phrases"]:

                phrase_in_output = contains_phrase(
                    normalized_sentence,
                    phrase,
                )

                phrase_in_original = contains_phrase(
                    normalized_original,
                    phrase,
                )

                if phrase_in_output and not phrase_in_original:

                    warning_key = (
                        category,
                        phrase,
                        normalized_sentence,
                    )

                    if warning_key in seen_warnings:
                        continue

                    warnings.append(
                        {
                            "category": category,
                            "phrase": phrase,
                            "generated_sentence": sentence,
                            "message": (
                                group_info["description"]
                                + " This phrase appears in the Llama output "
                                + "but not in the original source text. "
                                + "Manual checking is required."
                            ),
                        }
                    )

                    seen_warnings.add(warning_key)

                    break

            if len(warnings) >= max_warnings:
                break

        if len(warnings) >= max_warnings:
            break

    if warnings:
        return {
            "status": "warning",
            "warning_count": len(warnings),
            "warnings": warnings,
            "summary": (
                "Potential unsupported information was flagged. "
                "These warnings do not prove an error, but they should be "
                "manually checked against the source discharge summary."
            ),
        }

    return {
        "status": "pass",
        "warning_count": 0,
        "warnings": [],
        "summary": (
            "No high-risk unsupported wording patterns were detected. "
            "This is not proof of faithfulness; manual review is still recommended."
        ),
    }


def format_validator_result(validation_result):
    """
    Convert validation result into readable text for terminal testing.
    """

    lines = []

    lines.append("Faithfulness Validator Result")
    lines.append("=" * 32)
    lines.append(f"Status: {validation_result['status']}")
    lines.append(f"Warning count: {validation_result['warning_count']}")
    lines.append(f"Summary: {validation_result['summary']}")

    if validation_result["warnings"]:
        lines.append("")
        lines.append("Warnings:")

        for index, warning in enumerate(validation_result["warnings"], start=1):
            lines.append(f"{index}. Category: {warning['category']}")
            lines.append(f"   Phrase: {warning['phrase']}")
            lines.append(f"   Sentence: {warning['generated_sentence']}")
            lines.append(f"   Message: {warning['message']}")

    return "\n".join(lines)


if __name__ == "__main__":
    sample_original = """
    DISCHARGE SUMMARY

    The patient had bronchitis and shortness of breath.
    Chest X-ray did not show congestion or infiltrates.
    Exercise oximetry is pending to evaluate the need for home oxygen.
    Medication: Metoprolol 25 mg by mouth twice daily.
    Follow up with Pulmonology, Dr. Y.
    """

    sample_llama_output = """
    The patient had swelling in your lungs.
    You were given medicine through an IV to help with inflammation and fluid buildup.
    Your doctor also gave you medicine to help with your blood pressure and heart function.
    You'll also need a test to see if you need oxygen at home.
    Your doctor will check on you in the future to see how your lungs are doing.
    """

    result = validate_llama_output(sample_original, sample_llama_output)
    print(format_validator_result(result))
