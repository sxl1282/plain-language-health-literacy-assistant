"""Build and send the optional patient-friendly rewrite request to Ollama."""

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.simplifier import simplify_medical_text
from src.privacy import mask_identifiers


DEFAULT_MODEL = "llama3.1:8b"


# Keep deployment details outside the repository; local Ollama is the default.
OLLAMA_URL = os.getenv(
    "OLLAMA_URL",
    "http://localhost:11434/api/generate"
)
OLLAMA_TIMEOUT_SECONDS = int(
    os.getenv("OLLAMA_TIMEOUT_SECONDS", "120")
)


def clean_llama_output(text):
    """
    Clean Llama output for display.

    This removes:
    - unnecessary introductions
    - model-added notes/disclaimers
    - excessive blank lines

    It does not change the medical meaning of the output.
    """

    if not text:
        return ""

    text = text.strip()

    intro_patterns = [
        r"^here is the rewritten discharge summary in plain english:\s*",
        r"^here is a rewritten discharge summary in plain english:\s*",
        r"^here is the patient-friendly version:\s*",
        r"^patient-friendly version:\s*",
    ]

    for pattern in intro_patterns:
        text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

    # Remove model-generated final notes.
    cleaned_lines = []

    for line in text.splitlines():

        if re.match(
            r"^\s*(\*\*)?\s*note\s*:?",
            line,
            flags=re.IGNORECASE,
        ):
            break

        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines).strip()

    # Remove excessive blank lines.
    text = re.sub(
        r"\n\s*\n\s*\n+",
        "\n\n",
        text,
    )

    # Remove unnecessary spaces.
    cleaned_lines = []

    for line in text.splitlines():
        line = re.sub(
            r"[ \t]+",
            " ",
            line,
        ).strip()

        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)

    return text.strip()


def build_medical_terms_context(
    medical_terms,
    max_terms=30,
):
    """
    Build glossary context provided to Llama.
    """

    if not medical_terms:
        return "No glossary-supported medical terms were detected."

    lines = []

    for item in medical_terms[:max_terms]:

        term = item.get("term", "")
        explanation = item.get("explanation", "")

        if term and explanation:
            lines.append(
                f"- {term}: {explanation}"
            )

    return "\n".join(lines)


def build_prompt(
    original_text,
    medical_terms,
):
    """
    Build a strict faithfulness-focused prompt.
    """

    medical_terms_context = build_medical_terms_context(
        medical_terms
    )

    prompt = f"""
You are rewriting an English hospital discharge summary for a patient.

Your task:
Rewrite the discharge summary into clear and simple patient-friendly English.

Strict rules:

1. Use only information from the original discharge summary.
2. Do not add medical facts that are not explicitly stated.
3. Do not infer causes, risks, or explanations.
4. Do not say a medication was started, stopped, changed, prescribed,
or recommended unless the original text states this.
5. Do not explain why a test was performed unless the original text states it.
6. Do not add lifestyle advice or general health education.
7. Keep diagnoses, medications, doses, results, and follow-up information accurate.
8. Keep the original order and meaning.
9. Use short paragraphs.
10. Do not add introductions, summaries, or final notes.
11. Output only the rewritten discharge summary.

Medical terms and plain-language explanations:

{medical_terms_context}


Original discharge summary:

{original_text}
"""

    return prompt.strip()


def call_ollama(
    prompt,
    model=DEFAULT_MODEL,
):
    """
    Send request to Ollama server.
    """

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.8,
            "num_ctx": 4096,
            "num_predict": 900,
        },
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json"
        },
        method="POST",
    )

    with urllib.request.urlopen(
        request,
        timeout=OLLAMA_TIMEOUT_SECONDS,
    ) as response:

        result = json.loads(
            response.read().decode("utf-8")
        )

    return result.get(
        "response",
        "",
    ).strip()


def generate_llama_patient_friendly_version(
    original_text,
    medical_terms,
    model=DEFAULT_MODEL,
):
    """
    Generate Llama patient-friendly rewrite.
    """

    masked_text = mask_identifiers(original_text)

    prompt = build_prompt(
        original_text=masked_text,
        medical_terms=medical_terms,
    )

    llama_output = call_ollama(
        prompt=prompt,
        model=model,
    )

    return clean_llama_output(
        llama_output
    )


def main():
    """
    Command-line test entry point.
    """

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--file",
        required=True,
        help="Path to input text file.",
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Ollama model name.",
    )

    args = parser.parse_args()

    input_path = Path(args.file)

    original_text = input_path.read_text(
        encoding="utf-8"
    )

    simplification_result = simplify_medical_text(
        original_text,
        glossary_version="filtered",
    )

    medical_terms = simplification_result[
        "medical_terms"
    ]

    output = generate_llama_patient_friendly_version(
        original_text=original_text,
        medical_terms=medical_terms,
        model=args.model,
    )

    print(output)


if __name__ == "__main__":
    main()
