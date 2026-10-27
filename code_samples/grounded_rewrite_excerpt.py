"""Verbatim excerpts: retrieved glossary context and the constrained Llama prompt.

Selected from the original src/llama_simplifier.py; not a complete LLM client.
"""


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
