from src import pipeline
from src.pipeline import run_pipeline_from_text
from src.simplifier import simplify_medical_text


def test_empty_text_returns_structured_error():
    result = run_pipeline_from_text("   ")
    assert result["status"] == "error"
    assert result["error_type"] == "empty_input"


def test_known_medical_term_is_detected():
    result = simplify_medical_text("Diagnosis: Hypertension.")
    terms = {item["term"] for item in result["medical_terms"]}
    assert "hypertension" in terms


def test_medication_rewrite_does_not_infer_prescribing():
    result = run_pipeline_from_text("Medication: Amlodipine 5 mg once daily.")
    output = result["patient_friendly_version"].lower()
    assert "the discharge summary lists" in output
    assert "prescribed" not in output


def test_llama_failure_keeps_rule_based_output(monkeypatch):
    monkeypatch.setattr(
        pipeline,
        "generate_llama_version_if_requested",
        lambda **kwargs: {
            "status": "error",
            "message": "Llama generation unavailable.",
            "details": "test failure",
        },
    )
    result = run_pipeline_from_text(
        "Diagnosis: Hypertension.",
        use_llama=True,
    )
    assert result["status"] == "success"
    assert result["patient_friendly_version"]
    assert result["llama_patient_friendly_version"] is None
    assert result["llama_faithfulness_check"]["status"] == "not_run"
