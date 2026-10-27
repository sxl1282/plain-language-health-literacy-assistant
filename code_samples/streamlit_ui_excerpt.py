"""Selected verbatim UI functions from app/main.py; not the complete application."""

import html
import re

import streamlit as st


SCROLL_BOX_HEIGHT = 650


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
