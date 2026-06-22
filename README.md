# AI Agentic Compliance Workflow  Review System

> **An AI-powered document intelligence pipeline that analyses manufacturer PDFs, reconciles cross-document inconsistencies, maps coverage to Nepal import review requirements, and generates a professional compliance review draft.**

---

## Overview

SunBridge Trading (Kathmandu) is importing grid-tied solar inverters from China. Their Nepal import agent needs a compliance review document, but the manufacturer supplied two PDFs that may describe different product variants. This system automates the full analysis.

**Pipeline output:**

- `extracted_data.json` — structured product/manufacturer/specs data from each PDF
- `comparison_report.json` — field-level reconciliation with conflict detection and confidence scores
- `compliance_report.md` — professional Markdown draft for the Nepal agent

---

## Architecture

```
PDF Loader
    │
    ▼
Text Extraction Agent  ◄── GPT-4.1 (per PDF)
    │
    ▼
Data Normalization Agent
    │
    ▼
Reconciliation Agent  ◄── GPT-4.1 (cross-document comparison)
    │
    ▼
Compliance Mapping Agent  ◄── GPT-4.1 (NEPQA 2025 reference)
    │
    ▼
Report Generation Agent  ◄── GPT-4.1 (Markdown report)
```

Built on **LangGraph** (`StateGraph`) with a typed shared state (`GraphState`) flowing through all nodes.

---

## Technology Stack

| Layer           | Technology                  |
| --------------- | --------------------------- |
| Framework       | FastAPI + Uvicorn           |
| AI Workflow     | LangGraph + LangChain       |
| LLM             | OpenAI GPT-4.1              |
| Data validation | Pydantic v2                 |
| PDF extraction  | PyMuPDF (fitz) + pdfplumber |
| Testing         | pytest                      |
| Logging         | Rich                        |

---

## Project Structure

```
project/
│
├── app/
│   ├── agents/
│   │   └── nodes.py          # All LangGraph node implementations
│   ├── graph/
│   │   ├── state.py          # GraphState TypedDict
│   │   └── workflow.py       # LangGraph StateGraph builder
│   ├── models/
│   │   └── schemas.py        # All Pydantic v2 schemas
│   ├── prompts/
│   │   └── templates.py      # LLM prompt templates
│   ├── services/
│   │   ├── pdf_loader.py     # PyMuPDF + pdfplumber extraction
│   │   └── output_writer.py  # JSON / Markdown file writer
│   ├── utils/
│   │   ├── config.py         # Settings (pydantic-settings)
│   │   └── logger.py         # Rich logger
│   └── main.py               # FastAPI app
│
├── data/                     # Place PDFs here
├── outputs/                  # Generated output files
│   ├── extracted_data.json   # Sample output
│   ├── comparison_report.json
│   └── compliance_report.md
│
├── tests/
│   └── test_pipeline.py      # Unit + integration tests
│
├── run_review.py             # CLI entrypoint
├── requirements.txt
├── .env.example
├── DEMO_SCRIPT.md
└── README.md
```

---

## Setup

### 1. Prerequisites

- Python 3.11+
- OpenAI API key with GPT-4.1 access

### 2. Install dependencies

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
```

### 4. Place PDFs in `data/`

```
data/
├── DSS_GZES230100125901_combined-1.pdf
├── 188_1115.pdf
└── NEPQA_2025_Guideline.pdf
```

---

## Running

### CLI (recommended for assessment)

```bash
python run_review.py \
    --pdf1 data/DSS_GZES230100125901_combined-1.pdf \
    --pdf2 data/188_1115.pdf \
    --nepqa data/NEPQA_2025_Guideline.pdf \
    --output outputs/
```

Outputs are written to `outputs/` on completion.

### API server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Endpoints:**

| Method | Path                    | Description           |
| ------ | ----------------------- | --------------------- |
| GET    | `/health`             | Health check          |
| POST   | `/review`             | Review by file path   |
| POST   | `/review/upload`      | Review by file upload |
| GET    | `/outputs/{filename}` | Download output file  |

**Example request:**

```bash
curl -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{
    "pdf1_path": "data/DSS_GZES230100125901_combined-1.pdf",
    "pdf2_path": "data/188_1115.pdf",
    "nepqa_path": "data/NEPQA_2025_Guideline.pdf"
  }'
```

---

## Running Tests

```bash
# Unit tests (no API key required)
pytest tests/ -v

# Include integration test (requires OPENAI_API_KEY and PDFs in data/)
pytest tests/ -v -m integration
```

---

## Sample Outputs

Pre-generated sample outputs are in `outputs/`:

- [`outputs/extracted_data.json`](outputs/extracted_data.json)
- [`outputs/comparison_report.json`](outputs/comparison_report.json)
- [`outputs/compliance_report.md`](outputs/compliance_report.md)

---

## Key Design Decisions

### Honesty over fabrication

The system never invents compliance claims. If a field is absent from source documents, it returns `null` and flags the item as missing. NEPQA 2025 is used only as a reference map — the system does not claim conformance.

### Dual-extractor PDF loading

PyMuPDF and pdfplumber run in parallel on each PDF. The longer/more complete extraction is used as the primary, with unique lines from the other merged in. This improves coverage for complex PDFs with tables or mixed layouts.

### Contextual reconciliation

Rather than naive string comparison, the reconciliation agent uses GPT-4.1 to understand *why* values differ (e.g., different power ratings explain different output currents). Each comparison includes a confidence score and a human-readable notes field.

### Source traceability

Every extracted field carries a `source_pdf` attribute so the report can always trace claims back to their origin document.

### Pydantic v2 throughout

All data flows through typed Pydantic models. LLM JSON responses are validated before use. Invalid responses are caught and logged rather than crashing the pipeline.

---

## Notes for Assessors

- The system is designed around the actual task requirements (SunBridge Trading, grid-tied solar inverters, Nepal NBSM/NEPQA context)
- Prompt templates are in `app/prompts/templates.py` — they are specific to solar inverter compliance, not generic
- The `GraphState` TypedDict ensures type safety across all LangGraph nodes
- Error handling is consistent throughout — errors accumulate in `state["errors"]` and are reported without crashing the pipeline
- The demo script covers the full 5-minute demo as requested

---

## License

MIT
