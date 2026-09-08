# Evaluation and Testing Log

## 1. Purpose

This file records the main testing work carried out for the current prototype: **Plain-Language Health-Literacy Assistant for Patients**.

It is mainly a development and evaluation log, not the full dissertation evaluation chapter. It helps record what has been tested, what works, and what limitations should be discussed in the report.

The current system focuses on **English discharge summaries** only.

---

## 2. Current Version

Latest tested version:

```text
Final pre-submission GitLab version
```

Main components tested:

- Streamlit interface
- text input and image upload
- PaddleOCR for image input
- README-based medical glossary
- rule-based medical term detection
- citation linking to relevant source sentences
- rule-based plain-language baseline
- optional Llama 3.1 rewrite through Ollama
- best-effort local identifier masking before Llama processing
- configurable Ollama endpoint and timeout
- rule-based pipeline consistency check
- Llama faithfulness warning check
- AHRQ-informed questions to ask doctor
- safety and privacy notice

---

## 3. Text Input Test

I tested the text input mode with a short structured discharge summary.

The system worked as expected. It detected terms such as chest pain, hypertension, amlodipine, cardiology, and CT scan. It also generated medical term explanations, source sentence links, a rule-based plain-language version, questions to ask a doctor, and the safety notice.

The layout works better when the input includes clear discharge-summary headings, such as:

```text
DISCHARGE SUMMARY
DISCHARGE DIAGNOSES
HOSPITAL COURSE
DISCHARGE MEDICATIONS
PENDING RESULTS AND FOLLOW UP
```

Result: **Pass**

---

## 4. OCR Image Test

I tested the image input mode using:

```text
data/test_images/realistic_discharge_summary_sample.png
```

The image was generated using:

```text
scripts/generate_realistic_discharge_summary_image.py
```

The OCR pipeline ran successfully:

```text
image upload → OCR → term detection → citation → baseline output → optional Llama output → questions → safety notice
```

The system detected useful terms such as respiratory, bronchitis, renal failure, hypertension, hyperlipidemia, X-ray, MRSA, and Pulmonology.

Result: **Partial pass**

The image input works, but OCR formatting errors can still affect later outputs, especially with longer or less clear clinical text.

---

## 5. Batch Pipeline Test

I ran a lightweight batch test on all 108 processed discharge summaries.

This test used the rule-based pipeline only. I did not run Llama on all samples because Llama outputs require manual review.

Results:

```text
Successful samples: 108 / 108
Average detected terms: 40.03
Average generated questions: 6.0
Baseline warnings: 60 samples had 0 warnings, 48 samples had 1 warning
```

This shows that the rule-based pipeline can process the full discharge-summary dataset without crashing. However, this only tests technical pipeline behaviour. It does not prove that every explanation is readable or clinically correct.

Result: **Pass**

---

## 6. Glossary Filtering

Early testing showed that dictionary matching produced some false positives, such as:

```text
DISCHARGE
Sample
or
mg
pending
```

These terms were not always useful for patient-facing explanations.

After reviewing detected terms across the 108 discharge summaries, I updated the patient-facing glossary filtering.

Latest filtering result:

```text
Original README glossary entries: 7841
Kept patient-facing entries: 7790
Removed entries: 36
```

This made the **Medical Terms Explained** section cleaner. However, the method is still rule-based and cannot fully understand context.

---

## 7. Rule-Based Baseline

The rule-based baseline is useful because it is transparent and easy to inspect. It keeps the output closely linked to the original text and glossary explanations.

However, it can sound awkward because it directly inserts plain-language explanations into the original sentence structure. This is especially noticeable in longer discharge summaries.

The pipeline consistency check examines term matching, explanation availability, source sentence linking, and warning patterns. It does not prove clinical correctness, fluency, or readability.

Result: **Pass with limitation**

---

## 8. Llama 3.1 Output

The Llama 3.1 version is usually easier to read than the rule-based baseline. It often gives a clearer structure and more natural wording.

Before text is sent to Llama, the system applies best-effort local masking for common identifiers such as labelled names, dates of birth, IDs, phone numbers, emails, addresses, and dates. This reduces privacy risk but does not guarantee complete de-identification.

Llama can still omit details or add wording that is not clearly stated in the original discharge summary. Because of this, it is treated as an experimental rewrite, not as a clinically verified output.

Result: **Partial pass**

---

## 9. Llama Faithfulness Warning Check

I added a lightweight rule-based warning check for the Llama output.

It flags possible unsupported wording, such as causal explanations, medication-purpose explanations, advice-like wording, and general medical claims.

Example warning phrases include:

```text
because
led to
fluid buildup
to help with breathing
to help with allergies
to see if
you need to
```

A warning does not mean the output is definitely wrong. It means the sentence should be checked against the original discharge summary.

Result: **Pass**

---

## 10. Interface Testing

The Streamlit interface is now suitable for demo.

Recent improvements include:

- clearer display of original text and generated outputs
- explanation cards with source sentence links
- repeated terms sharing the same citation marker
- Llama failure handled with a user-friendly fallback message
- no technical exception details shown to users
- warning when a remote HTTP Ollama endpoint is configured
- privacy notice for sample or de-identified records only

Result: **Pass**

---

## 11. Main Limitations

The main limitations are:

- OCR can still produce formatting errors
- glossary matching does not fully understand context
- rule-based rewriting can be awkward or noisy
- Llama output is more readable but may omit or add information
- citation is sentence-level, not exact phrase-level
- validators are warning tools only, not proof of medical correctness
- best-effort identifier masking may miss names or indirect identifiers in free text
- the user evaluation was small and non-clinical

These limitations should be discussed clearly in the dissertation.

---

## 12. Safety Boundary

The system is for educational support only.

It does not diagnose patients, recommend treatment, suggest medication changes, make clinical decisions, or replace healthcare professionals.

The generated questions are designed to help patients communicate with clinicians, not to provide medical advice directly.

---

## 13. Current Conclusion

The prototype now works as an end-to-end proof of concept.

Text input works well with structured discharge summaries. Image input also works, although OCR quality can affect later outputs.

The rule-based baseline is useful for transparency and traceability. The Llama version improves readability, but it still needs warning checks and human review.

Overall, the system is ready for dissertation demo, as long as its limitations are explained clearly.