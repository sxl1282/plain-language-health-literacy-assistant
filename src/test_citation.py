from src.citation import create_citations, highlight_terms
from src.simplifier import simplify_medical_text


def test_repeated_term_collects_all_source_sentences():
    text = "Diagnosis: Hypertension. Hypertension remained stable."
    terms = simplify_medical_text(text)["medical_terms"]
    citations = create_citations(text, terms)
    item = next(c for c in citations if c["term"] == "hypertension")

    assert item["source_sentences"] == [
        "Diagnosis: Hypertension.",
        "Hypertension remained stable.",
    ]
    assert highlight_terms(text, citations).count(item["marker"]) == 2
