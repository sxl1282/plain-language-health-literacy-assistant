"""Streamlit interface for text and image discharge-summary inputs."""

import html
import logging
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st


# Allow the app to be launched with: streamlit run app/main.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))


from src.pipeline import run_pipeline_from_text, run_pipeline_from_image


SCROLL_BOX_HEIGHT = 650
LOGGER = logging.getLogger(__name__)


SECTION_HEADINGS = [
    "DISCHARGE SUMMARY",
    "DISCHARGE DIAGNOSES",
    "SECONDARY DIAGNOSES",
    "HOSPITAL COURSE",
    "DISPOSITION",
    "DISCHARGE MEDICATIONS",
    "NEW MEDICATIONS",
    "PENDING RESULTS AND FOLLOW UP",
    "PAST MEDICAL HISTORY",
    "PHYSICAL EXAMINATION",
    "LABORATORY DATA",
]


PATIENT_INFO_LABELS = [
    "Patient Name:",
    "Date of Discharge:",
    "Hospital:",
]


def normalize_discharge_text_for_layout(text):
    """
    Normalize OCR or pasted discharge-summary text for display layout.

    This is display-only formatting. It does not change the backend text
    used for medical term detection, citation, rewriting, or evaluation.
    """

    if not text:
        return ""

    text = html.unescape(str(text))
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Clean common OCR punctuation artifacts.
    text = text.replace(".,", ". ")
    text = text.replace(",.", ". ")
    text = text.replace(";,", ". ")
    text = text.replace(",:", ": ")
    text = text.replace(" ,", ",")
    text = text.replace(" .", ".")

    # Normalize spacing.
    text = re.sub(r"\s+", " ", text).strip()

    # Normalize follow-up spelling for display consistency.
    text = re.sub(
        r"\bFOLLOW\s*-\s*UP\b",
        "FOLLOW-UP",
        text,
        flags=re.IGNORECASE,
    )

    # Put section headings on separate lines.
    for heading in sorted(SECTION_HEADINGS, key=len, reverse=True):
        text = re.sub(
            rf"\s*({re.escape(heading)})(\s*:)?\s*",
            rf"\n\n{heading}\n",
            text,
            flags=re.IGNORECASE,
        )

    # Put patient information labels on separate lines.
    for label in PATIENT_INFO_LABELS:
        text = re.sub(
            rf"\s*({re.escape(label)})",
            rf"\n{label}",
            text,
            flags=re.IGNORECASE,
        )

    # Put numbered clinical list items on separate lines.
    text = re.sub(r"\s+(\d{1,2}\.)\s*", r"\n\1 ", text)

    # Clean repeated blank lines.
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

    return text.strip()


def get_canonical_heading(line):
    """
    Return canonical section heading if a line is a known heading.
    """

    normalized_line = line.strip().rstrip(":").upper()

    for heading in SECTION_HEADINGS:
        if normalized_line == heading.upper():
            return heading

    return None


def is_patient_info_line(line):
    """
    Check whether a line contains patient information.
    """

    line_lower = line.lower().strip()

    return any(
        line_lower.startswith(label.lower())
        for label in PATIENT_INFO_LABELS
    )


def highlight_terms_in_html_text(text, citations):
    """
    Highlight detected medical terms in escaped HTML text.
    """

    highlighted_text = html.escape(text)

    # Match longer terms first so phrases such as "CT scan"
    # are highlighted before shorter terms such as "CT".
    sorted_citations = sorted(
        citations,
        key=lambda item: len(item.get("matched_text", item.get("term", ""))),
        reverse=True,
    )

    for item in sorted_citations:

        term = item.get("matched_text", item.get("term", ""))
        marker = item.get("marker", "")

        if not term or not marker:
            continue

        escaped_term = html.escape(term)

        pattern = (
            r"(?<![A-Za-z0-9])"
            + re.escape(escaped_term)
            + r"(?![A-Za-z0-9])"
        )

        highlighted_text = re.sub(
            pattern,
            lambda match: (
                "<mark style='background-color:#fff176; color:#111111; "
                "padding:2px 4px; border-radius:3px;'>"
                f"{match.group(0)}{html.escape(marker)}"
                "</mark>"
            ),
            highlighted_text,
            flags=re.IGNORECASE,
        )

    return highlighted_text


def format_line_html(line, citations=None):
    """
    Format one line as HTML.

    If citations are provided, detected terms are highlighted.
    Otherwise, the text is only HTML-escaped.
    """

    if citations:
        return highlight_terms_in_html_text(line, citations)

    return html.escape(line)


def build_discharge_document_html(text, citations=None):
    """
    Build discharge-summary-style HTML layout.

    This layout is used for:
    1. Original Text with Highlighted Medical Terms
    2. Patient-Friendly Version - Rule-based Baseline

    It restores section headings, numbered lists, patient information,
    and readable paragraphs.
    """

    normalized_text = normalize_discharge_text_for_layout(text)

    if not normalized_text:
        return ""

    raw_lines = [
        line.strip(" ,;")
        for line in normalized_text.split("\n")
        if line.strip(" ,;")
    ]

    html_parts = []

    for line in raw_lines:

        heading = get_canonical_heading(line)

        if heading:
            heading_tag = "h3" if heading == "DISCHARGE SUMMARY" else "h4"

            html_parts.append(
                f"<{heading_tag} style='margin-top:26px; margin-bottom:14px; "
                f"color:#111111; font-weight:800; letter-spacing:0.3px;'>"
                f"{html.escape(heading)}</{heading_tag}>"
            )

            if heading == "DISCHARGE SUMMARY":
                html_parts.append(
                    "<hr style='border:none; border-top:1px solid #222222; "
                    "margin-top:8px; margin-bottom:22px;'>"
                )

            continue

        if is_patient_info_line(line):
            html_parts.append(
                f"<p style='margin-top:0; margin-bottom:6px; "
                f"line-height:1.55; font-size:16px;'>"
                f"{format_line_html(line, citations)}</p>"
            )
            continue

        if re.match(r"^\d+\.", line):
            html_parts.append(
                f"<p style='margin-top:0; margin-bottom:10px; "
                f"margin-left:18px; line-height:1.7; font-size:16px;'>"
                f"{format_line_html(line, citations)}</p>"
            )
            continue

        # Split very long paragraphs into sentence-level chunks for readability.
        if len(line) > 650:
            sentences = re.split(r"(?<=[.!?])\s+", line)

            for sentence in sentences:
                sentence = sentence.strip()

                if sentence:
                    html_parts.append(
                        f"<p style='margin-top:0; margin-bottom:12px; "
                        f"line-height:1.7; font-size:16px;'>"
                        f"{format_line_html(sentence, citations)}</p>"
                    )

        else:
            html_parts.append(
                f"<p style='margin-top:0; margin-bottom:12px; "
                f"line-height:1.7; font-size:16px;'>"
                f"{format_line_html(line, citations)}</p>"
            )

    return "".join(html_parts)


def display_document_box(document_html, height=SCROLL_BOX_HEIGHT):
    """
    Display formatted document HTML inside a fixed scrollable box.
    """

    box_html = (
        "<div style='"
        "background-color:#f8f9fa; "
        "color:#111111; "
        "padding:20px 26px; "
        "border-radius:8px; "
        "border:1px solid #dddddd; "
        "line-height:1.7; "
        "font-size:16px; "
        "white-space:normal;"
        "'>"
        f"{document_html}"
        "</div>"
    )

    with st.container(height=height, border=True):
        st.markdown(box_html, unsafe_allow_html=True)


def display_pipeline_error(result):
    """Display a safe message for an expected pipeline error."""

    error_message = result.get(
        "error_message",
        "The document could not be processed.",
    )

    st.error(error_message)

    if result.get("error_type") == "ocr_empty":
        st.info(
            "Please try a clearer image with readable English text. "
            "The system did not continue to medical term detection or question generation."
        )


def display_original_text(result):
    """
    Display the original text with highlighted medical terms.
    """

    st.subheader("Original Text with Highlighted Medical Terms")

    highlighted_html = build_discharge_document_html(
        text=result["original_text"],
        citations=result["citations"],
    )

    display_document_box(
        document_html=highlighted_html,
        height=SCROLL_BOX_HEIGHT,
    )


def display_medical_terms(result):
    """
    Display medical terms, explanations, and source sentences.
    """

    st.subheader("Medical Terms Explained")

    with st.container(height=SCROLL_BOX_HEIGHT, border=True):

        if not result["citations"]:
            st.info("No glossary-supported medical terms were detected.")
            return

        for item in result["citations"]:

            term = html.escape(item["term"])
            explanation = html.escape(item["explanation"])
            source_sentences = item.get("source_sentences") or [item["source"]]
            source = "<br>".join(
                html.escape(sentence)
                for sentence in source_sentences
                if sentence
            )

            card_html = (
                "<div style='"
                "background-color:#ffffff; "
                "color:#111111; "
                "padding:14px; "
                "border-radius:8px; "
                "border:1px solid #dddddd; "
                "margin-bottom:10px; "
                "line-height:1.6; "
                "font-size:15px;"
                "'>"
                f"<b>{html.escape(item['marker'])} {term}</b><br>"
                f"<b>Explanation:</b> {explanation}<br>"
                f"<b>Source:</b> {source}"
                "</div>"
            )

            st.markdown(card_html, unsafe_allow_html=True)


def estimate_patient_friendly_box_height(text):
    """
    Estimate a suitable display box height based on text length.

    Short text gets a smaller box. Long text is capped so the page
    remains readable and scrollable.
    """

    if not text:
        return 220

    text = str(text)

    line_break_count = text.count("\n") + 1
    estimated_wrapped_lines = len(text) // 95 + 1

    estimated_lines = max(
        line_break_count,
        estimated_wrapped_lines,
    )

    estimated_height = estimated_lines * 32 + 120

    return min(
        max(estimated_height, 280),
        SCROLL_BOX_HEIGHT,
    )


def display_patient_friendly_version(result):
    """
    Display the rule-based patient-friendly version.

    This keeps the generated rule-based baseline text unchanged.
    Only the visual display is reformatted into discharge-summary layout.
    """

    st.header("Patient-Friendly Version - Rule-based Baseline")

    st.caption(
        "This version is generated using the rule-based glossary replacement "
        "baseline. It is kept for comparison with the Llama 3.1 version."
    )

    patient_friendly_text = result["patient_friendly_version"]

    if not patient_friendly_text:
        st.info("No patient-friendly version was generated.")
        return

    formatted_html = build_discharge_document_html(
        text=patient_friendly_text,
        citations=None,
    )

    box_height = estimate_patient_friendly_box_height(
        patient_friendly_text
    )

    display_document_box(
        document_html=formatted_html,
        height=box_height,
    )


def display_baseline_faithfulness_check(result):
    """
    Display term-level validation result for the rule-based baseline.
    """

    check = result.get("baseline_faithfulness_check", {})

    st.header("Rule-based Pipeline Consistency Check")

    st.caption(
        "This checks term matching, explanation availability, source-sentence linking, "
        "and possible over-detection. It does not establish clinical correctness."
    )

    status = check.get("status", "not_run")
    warning_count = check.get("warning_count", 0)
    summary = check.get("summary", "")

    if status == "pass":
        st.success(
            "No configured internal consistency warning patterns were detected. "
            "Manual review is still required."
        )

    elif status == "warning":
        st.warning(f"{warning_count} possible baseline issue(s) detected.")
        st.write(summary)

        for index, warning in enumerate(check.get("warnings", []), start=1):
            with st.expander(f"Warning {index}: {warning.get('category', '')}"):
                st.write(f"**Term:** {warning.get('term', '')}")
                st.write(f"**Message:** {warning.get('message', '')}")

    else:
        st.info(summary)


def display_llama_patient_friendly_version(result):
    """
    Display the Llama-based patient-friendly version if it was generated.

    If Llama generation fails, show a clear warning instead of displaying
    the failure message as normal patient-facing output.
    """

    llama_status = result.get("llama_generation_status")
    llama_text = result.get("llama_patient_friendly_version", "")

    if llama_status and llama_status.get("status") == "error":

        st.header("Patient-Friendly Version - Llama 3.1")

        st.error(
            "Llama version unavailable. "
            "Rule-based baseline is still available."
        )

        return

    if not llama_text:
        return

    st.header("Patient-Friendly Version - Llama 3.1")

    st.caption(
        "This version is generated by Llama 3.1 using the original discharge "
        "summary and the detected glossary-based explanations. It is shown "
        "for comparison with the rule-based baseline."
    )

    safe_text = html.escape(llama_text)

    box_height = estimate_patient_friendly_box_height(
        llama_text
    )

    llama_html = (
        "<div style='"
        "background-color:#f8f9fa; "
        "color:#111111; "
        "padding:18px 22px; "
        "border-radius:8px; "
        "border:1px solid #dddddd; "
        "line-height:1.75; "
        "font-size:16px; "
        "white-space:pre-wrap;"
        "'>"
        f"{safe_text}"
        "</div>"
    )

    with st.container(height=box_height, border=True):
        st.markdown(llama_html, unsafe_allow_html=True)


def display_llama_faithfulness_check(result):
    """
    Display output-level validation result for the Llama output.
    """

    check = result.get("llama_faithfulness_check", {})

    if not result.get("llama_patient_friendly_version"):
        return

    st.header("Faithfulness Check for Llama 3.1")

    st.caption(
        "This checks possible unsupported medication changes, causal explanations, "
        "test purposes, advice, and general medical claims. It is a lightweight "
        "warning system, not an automatic proof of correctness."
    )

    status = check.get("status", "not_run")
    warning_count = check.get("warning_count", 0)
    summary = check.get("summary", "")

    if status == "pass":
        st.success(
            "No configured high-risk wording patterns were detected. "
            "This is not proof of faithfulness."
        )

    elif status == "warning":
        st.warning(
            f"{warning_count} possible unsupported information warning(s) detected."
        )
        st.write(summary)

        for index, warning in enumerate(check.get("warnings", []), start=1):
            with st.expander(f"Warning {index}: {warning.get('category', '')}"):
                st.write(f"**Phrase:** {warning.get('phrase', '')}")
                st.write(
                    f"**Generated sentence:** {warning.get('generated_sentence', '')}"
                )
                st.write(f"**Message:** {warning.get('message', '')}")

    else:
        st.info(summary)


def display_questions(result):
    """
    Display generated questions to ask a doctor.
    """

    st.header("Questions to Ask Doctor")

    if not result["questions"]:
        st.info("No questions were generated.")
        return

    for question in result["questions"]:
        st.markdown(f"- {html.escape(question)}")


def display_safety_notice(result):
    """
    Display safety notice.
    """

    st.header("Safety Notice")
    st.info(result["safety_notice"])


def display_result(result):
    """
    Display all pipeline outputs using a two-column layout.

    Error results are shown as errors and do not display Processing complete.
    """

    if result.get("status") == "error":
        display_pipeline_error(result)
        return

    st.success("Processing complete.")

    left_column, right_column = st.columns([1.25, 1])

    with left_column:
        display_original_text(result)

    with right_column:
        display_medical_terms(result)

    st.markdown("---")

    display_patient_friendly_version(result)

    display_baseline_faithfulness_check(result)

    display_llama_patient_friendly_version(result)

    display_llama_faithfulness_check(result)

    display_questions(result)

    display_safety_notice(result)


def save_uploaded_file(uploaded_file):
    """
    Save uploaded image to a temporary file and return the path.
    """

    file_suffix = Path(uploaded_file.name).suffix.lower()

    if not file_suffix:
        file_suffix = ".png"

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=file_suffix,
    ) as temp_file:

        temp_file.write(uploaded_file.getbuffer())
        temp_path = temp_file.name

    return temp_path


def remove_temp_file(file_path):
    """
    Remove temporary uploaded file after processing.
    """

    if not file_path:
        return

    try:
        if os.path.exists(file_path):
            os.remove(file_path)

    except OSError:
        pass


def uses_remote_http_ollama():
    """Return True when the configured Ollama URL is remote and unencrypted."""
    url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
    parsed = urlparse(url)
    return (
        parsed.scheme == "http"
        and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
    )


def show_unexpected_error(error):
    """Log technical details and keep them out of the patient-facing UI."""
    LOGGER.exception("Input processing failed", exc_info=error)
    st.error(
        "Something went wrong while processing this input. Please try again "
        "with a clearer sample or de-identified text."
    )


def main():
    """
    Main Streamlit application.
    """

    st.set_page_config(
        page_title="Plain-Language Health-Literacy Assistant",
        page_icon="🏥",
        layout="wide",
    )

    st.title("Plain-Language Health-Literacy Assistant")

    st.write(
        "This prototype helps patients understand English discharge summaries. "
        "It identifies medical terms, explains them in plain language, links each "
        "explanation to relevant source sentences, and generates questions to ask a doctor."
    )

    st.warning(
        "This tool is for educational support only. "
        "It does not provide diagnosis, treatment decisions, or medication advice."
    )

    st.info(
        "For testing, please use sample or de-identified discharge summaries only. "
        "Do not upload real identifiable patient information to this prototype."
    )

    input_mode = st.radio(
        "Choose input mode",
        [
            "Paste discharge summary text",
            "Upload discharge summary image",
        ],
    )

    generate_llama = st.checkbox(
        "Generate Llama 3.1 Patient-Friendly Version (slower)",
        value=False,
        help=(
            "If selected, the system will generate an additional Llama-based "
            "patient-friendly version using the original text and detected "
            "medical term explanations."
        ),
    )

    if generate_llama:
        st.info(
            "Llama 3.1 generation uses the configured Ollama server. "
            "Common identifiers are masked locally before the request, but this "
            "does not guarantee complete de-identification."
        )
        if uses_remote_http_ollama():
            st.warning(
                "The configured remote Ollama connection is not encrypted. "
                "Use synthetic or de-identified records only."
            )

    sample_text = """DISCHARGE SUMMARY
Patient Name: Sample Patient
Date of Discharge: 12 March 2026
Hospital: Sample General Hospital

DISCHARGE DIAGNOSES
1. Hypertension.
2. Chest pain.

HOSPITAL COURSE
The patient was admitted with chest pain.
CT scan was performed and the result is pending.

DISCHARGE MEDICATIONS
1. Amlodipine 5 mg once daily.

PENDING RESULTS AND FOLLOW UP
The patient will follow up with cardiology clinic."""

    if input_mode == "Paste discharge summary text":

        discharge_summary = st.text_area(
            "Discharge Summary Text",
            value=sample_text,
            height=220,
        )

        if st.button("Generate Plain-Language Explanation"):

            if not discharge_summary.strip():
                st.error("Please paste a discharge summary first.")
                return

            spinner_message = "Processing discharge summary..."

            if generate_llama:
                spinner_message = (
                    "Processing discharge summary and generating Llama 3.1 "
                    "version. This may take several minutes..."
                )

            try:
                with st.spinner(spinner_message):
                    result = run_pipeline_from_text(
                        discharge_summary,
                        glossary_version="filtered",
                        use_llama=generate_llama,
                    )
            except Exception as error:
                show_unexpected_error(error)
                return

            display_result(result)

    else:

        uploaded_file = st.file_uploader(
            "Upload an English discharge summary image",
            type=["png", "jpg", "jpeg"],
        )

        if uploaded_file is not None:

            st.image(
                uploaded_file,
                caption="Uploaded discharge summary image",
                use_container_width=True,
            )

            if st.button("Extract Text and Generate Explanation"):

                spinner_message = (
                    "Running OCR and processing discharge summary. "
                    "This may take a moment..."
                )

                if generate_llama:
                    spinner_message = (
                        "Running OCR, processing discharge summary, and generating "
                        "Llama 3.1 version. This may take several minutes..."
                    )

                image_path = None

                try:
                    with st.spinner(spinner_message):
                        image_path = save_uploaded_file(uploaded_file)
                        result = run_pipeline_from_image(
                            image_path,
                            glossary_version="filtered",
                            use_llama=generate_llama,
                        )
                except Exception as error:
                    show_unexpected_error(error)
                    return
                finally:
                    remove_temp_file(image_path)

                display_result(result)


if __name__ == "__main__":
    main()
