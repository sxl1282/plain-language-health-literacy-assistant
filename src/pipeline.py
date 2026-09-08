"""Connect the term, citation, rewriting, warning, and question modules."""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))


from src.simplifier import simplify_medical_text
from src.citation import create_citations, highlight_terms
from src.summarizer import generate_patient_friendly_version
from src.question_generator import generate_questions
from src.baseline_validator import validate_baseline_output
from src.llama_validator import validate_llama_output


def generate_llama_version_if_requested(
    text,
    medical_terms,
    use_llama=False,
    llama_model="llama3.1:8b",
):
    """Generate the optional Llama rewrite without using the baseline output."""

    if not use_llama:
        return None

    try:
        from src.llama_simplifier import generate_llama_patient_friendly_version

        output = generate_llama_patient_friendly_version(
            original_text=text,
            medical_terms=medical_terms,
            model=llama_model,
        )

        return {
            "status": "success",
            "content": output,
        }

    except Exception as error:

        return {
            "status": "error",
            "message": "Llama generation unavailable.",
            "details": str(error),
        }


def validate_llama_if_available(
    original_text,
    llama_result,
):
    """
    Run Llama faithfulness validation only for valid output.
    """

    if not llama_result:

        return {
            "status": "not_run",
            "warning_count": 0,
            "warnings": [],
            "summary": (
                "Llama output was not requested."
            ),
        }


    if llama_result.get("status") != "success":

        return {
            "status": "not_run",
            "warning_count": 0,
            "warnings": [],
            "summary": (
                "Llama output unavailable, "
                "so faithfulness validation was skipped."
            ),
        }


    return validate_llama_output(
        original_text=original_text,
        llama_output=llama_result["content"],
    )


def run_pipeline_from_text(
    text,
    glossary_version="filtered",
    use_llama=False,
    llama_model="llama3.1:8b",
):
    """
    Run the complete pipeline from pasted discharge-summary text.
    """

    if not text or not text.strip():

        return {
            "status": "error",
            "error_type": "empty_input",
            "error_message": (
                "No discharge summary text was provided."
            ),
        }


    simplification_result = simplify_medical_text(
        text,
        glossary_version=glossary_version,
    )


    medical_terms = simplification_result["medical_terms"]


    citations = create_citations(
        text,
        medical_terms,
    )


    highlighted_text = highlight_terms(
        text,
        citations,
    )


    rule_based_patient_friendly_version = (
        generate_patient_friendly_version(
            text,
            medical_terms,
        )
    )


    baseline_faithfulness_check = (
        validate_baseline_output(
            original_text=text,
            medical_terms=medical_terms,
            citations=citations,
            patient_friendly_version=(
                rule_based_patient_friendly_version
            ),
        )
    )


    llama_result = generate_llama_version_if_requested(
        text=text,
        medical_terms=medical_terms,
        use_llama=use_llama,
        llama_model=llama_model,
    )


    llama_patient_friendly_version = None

    if llama_result and llama_result.get("status") == "success":

        llama_patient_friendly_version = (
            llama_result["content"]
        )


    llama_faithfulness_check = (
        validate_llama_if_available(
            original_text=text,
            llama_result=llama_result,
        )
    )


    questions = generate_questions(
        text,
        medical_terms,
    )


    return {

        "status": "success",

        "input_type": "text",

        "glossary_version": glossary_version,

        "original_text": text,

        "highlighted_text": highlighted_text,

        "medical_terms": medical_terms,

        "citations": citations,

        "patient_friendly_version":
            rule_based_patient_friendly_version,

        "baseline_faithfulness_check":
            baseline_faithfulness_check,

        "llama_patient_friendly_version":
            llama_patient_friendly_version,

        "llama_generation_status":
            llama_result,

        "llama_faithfulness_check":
            llama_faithfulness_check,

        "questions": questions,

        "safety_notice": (
            "This tool provides educational explanations only. "
            "It does not provide diagnosis, treatment decisions, "
            "or medication advice. Please consult a qualified doctor."
        ),
    }



def run_pipeline_from_image(
    image_path,
    glossary_version="filtered",
    use_llama=False,
    llama_model="llama3.1:8b",
):
    """
    Run the complete pipeline from discharge-summary image.
    """

    from src.ocr import extract_text_from_image


    extracted_text = extract_text_from_image(
        image_path
    )


    if not extracted_text or not extracted_text.strip():

        return {

            "status": "error",

            "error_type": "ocr_empty",

            "error_message": (
                "No readable text was detected. "
                "Please upload a clearer image."
            ),

            "input_type": "image",

            "image_path": image_path,
        }



    result = run_pipeline_from_text(
        extracted_text,
        glossary_version=glossary_version,
        use_llama=use_llama,
        llama_model=llama_model,
    )


    result["input_type"] = "image"

    result["image_path"] = image_path


    return result



if __name__ == "__main__":

    sample_text = """
    DISCHARGE SUMMARY

    Patient Name: Sample Patient

    DISCHARGE DIAGNOSES

    1. Hypertension.
    2. Chest pain.

    DISCHARGE MEDICATIONS

    1. Amlodipine 5 mg once daily.

    PENDING RESULTS AND FOLLOW UP

    Follow-up with cardiology clinic.
    """


    output = run_pipeline_from_text(
        sample_text,
        use_llama=False,
    )


    print("Detected Medical Terms:")

    for item in output["medical_terms"]:
        print(
            f"- {item['term']}: {item['explanation']}"
        )


    print("\nRule-based Patient-Friendly Version:")
    print(
        output["patient_friendly_version"]
    )


    print("\nBaseline Check:")
    print(
        output["baseline_faithfulness_check"]
    )


    print("\nLlama Check:")
    print(
        output["llama_faithfulness_check"]
    )


    print("\nQuestions:")

    for question in output["questions"]:
        print(
            f"- {question}"
        )
