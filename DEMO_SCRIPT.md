# 5-Minute Video Demo Script
## Cantordust Nepal Compliance Review — AI Engineer Assessment

---

### [0:00 – 0:30] Introduction

> "Hi, I'm demonstrating the Cantordust Nepal Import Compliance Review system —
> an AI-powered document intelligence pipeline built for the AI Engineer Assessment.
>
> The problem: SunBridge Trading in Kathmandu is importing grid-tied solar inverters
> from China. Their Nepal import agent needs a compliance review document, but the
> manufacturer sent two PDFs that may describe different product variants — and neither
> directly addresses Nepal's import requirements.
>
> My solution automates the full review process: PDF extraction → structured data →
> cross-document reconciliation → Nepal compliance mapping → professional draft report."

---

### [0:30 – 1:30] Architecture Overview

> "The system is built on LangGraph with six nodes forming a directed pipeline.
>
> [Show diagram]
>
> Node 1 — PDF Loader: Uses PyMuPDF and pdfplumber in parallel. Both extractors
> run on each PDF; the system picks the more complete output and merges unique content.
>
> Node 2 — Text Extraction Agent: Sends each PDF's text to GPT-4.1 with a structured
> extraction prompt. Returns a typed Pydantic model containing product info, manufacturer,
> specs, certifications, test reports, and labeling data.
>
> Node 3 — Data Normalization: Cleans null values, normalises units, and strips
> boilerplate strings like 'N/A' or 'Unknown'.
>
> Node 4 — Reconciliation Agent: Compares both extracted documents field-by-field.
> GPT-4.1 classifies each field as exact match, partial match, conflict, or missing.
> Every comparison gets a confidence score.
>
> Node 5 — Compliance Mapping: Cross-references the merged data against NEPQA 2025
> guideline sections. Maps coverage status for each Nepal import review section.
> Never invents compliance claims.
>
> Node 6 — Report Generation: Produces a professional Markdown draft with status
> icons, tables, and actionable recommendations."

---

### [1:30 – 2:30] Running the Pipeline

> "Let me run the CLI now.
>
> [Terminal]
> python run_review.py \
>     --pdf1 data/DSS_GZES230100125901_combined-1.pdf \
>     --pdf2 data/188_1115.pdf \
>     --nepqa data/NEPQA_2025_Guideline.pdf \
>     --output outputs/
>
> You can see the nodes executing in sequence. The pipeline logs each step with
> Rich-formatted output. Total runtime on GPT-4.1 is typically 60–90 seconds.
>
> [Output summary shown]
> Reconciliation: 12 exact matches, 4 partial, 6 conflicts, 4 missing in both.
> Confidence: 0.82"

---

### [2:30 – 3:30] Reconciliation Logic

> "The most interesting engineering challenge was reconciliation.
>
> The two PDFs turned out to describe *different power variants* — 3kW and 5kW —
> not the same product. A naive diff would flag everything as conflicting.
>
> The reconciliation agent uses GPT-4.1 to understand *context*: it recognises that
> a difference in 'rated output current' between 13A and 21.7A is *consistent with*
> different power ratings, not a contradiction.
>
> [Show comparison_report.json]
>
> Each conflict gets a 'notes' field explaining the assessment. For example:
> - 'rated_power_w': 3000W vs 5000W → status: conflict, confidence: 0.95,
>   note: 'SIGNIFICANT: PDFs describe different power variants. SunBridge must
>   confirm which variant is being imported.'
>
> Meanwhile, shared architecture details — IP65, operating range, MPPT range,
> efficiency, THD — are flagged as exact matches with confidence 1.0.
>
> The system also surfaces the most important gap: no Nepal NBSM/NEPQA type-approval
> certificate in either document — flagged as 'missing_in_both' with confidence 1.0."

---

### [3:30 – 4:30] Nepal Compliance Mapping & Report

> "The compliance mapping node uses NEPQA 2025 purely as a reference guide —
> it maps each section to available documentation and honestly states what's missing.
>
> [Show compliance_report.md in browser/editor]
>
> The report contains:
> - Status icons: ✅ Verified, ⚠️ Partial, ❌ Missing, 🔴 Conflict
> - Tables comparing PDF 1 vs PDF 2 for every key field
> - A prioritised recommendations list for SunBridge
>
> The most critical finding — the missing Nepal type-approval certificate — is flagged
> as Critical in section 11.5 and in the Executive Summary table.
>
> The report is honest: it says 'TÜV Rheinland certificates referenced but original
> documents not confirmed' — it never claims certification is complete."

---

### [4:30 – 5:00] API & Closing

> "The system also exposes a FastAPI server.
>
> [Terminal]
> uvicorn app.main:app --reload
>
> POST /review  — accepts file paths
> POST /review/upload  — accepts file uploads directly
> GET /outputs/{filename}  — downloads generated files
>
> Three JSON/Markdown output files are written to the outputs/ directory:
> extracted_data.json, comparison_report.json, and compliance_report.md.
>
> In summary: this pipeline handles multi-document PDF intelligence, honest
> conflict detection, and compliance-aware reporting — all in a modular,
> production-ready LangGraph architecture.
>
> The code is fully typed with Pydantic v2, includes unit tests, and has
> zero hardcoded assumptions or fabricated compliance claims.
>
> Thank you."

---

*Total: ~5 minutes*
