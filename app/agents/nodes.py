"""
app/agents/nodes.py
All LangGraph node implementations.
Each node is a pure function: GraphState -> GraphState (partial update dict).
"""
from __future__ import annotations

import json
import traceback
from typing import Any

from langchain_openai import ChatOpenAI # type: ignore
from langchain_core.messages import SystemMessage, HumanMessage

from app.graph.state import GraphState
from app.models.schemas import (
    ExtractedDocument,
    ProductInfo,
    ManufacturerInfo,
    TechnicalSpecs,
    CertificationInfo,
    TestReportInfo,
    LabelingInfo,
    ReconciliationReport,
    FieldComparison,
    MatchStatus,
    NepalComplianceMap,
    NepalComplianceSection,
    ComplianceReport,
    InfoStatus,
)
from app.prompts.templates import (
    EXTRACTION_SYSTEM, EXTRACTION_HUMAN,
    RECONCILIATION_SYSTEM, RECONCILIATION_HUMAN,
    COMPLIANCE_SYSTEM, COMPLIANCE_HUMAN,
    REPORT_SYSTEM, REPORT_HUMAN,
)
from app.services.pdf_loader import load_pdf
from app.utils.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


def _get_llm(temperature: float | None = None) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.openai_model,
        temperature=temperature if temperature is not None else settings.openai_temperature,
        max_tokens=settings.openai_max_tokens,
        api_key=settings.openai_api_key,
    )


def _safe_llm_json(system: str, human: str) -> dict[str, Any]:
    """Call LLM and safely parse JSON response."""
    llm = _get_llm()
    messages = [SystemMessage(content=system), HumanMessage(content=human)]
    response = llm.invoke(messages)
    raw = response.content.strip()
    # Strip possible markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    return json.loads(raw)


def _truncate(text: str, max_chars: int = 12000) -> str:
    return text[:max_chars] if len(text) > max_chars else text


# ---------------------------------------------------------------------------
# Node 1: PDF Loader
# ---------------------------------------------------------------------------

def pdf_loader_node(state: GraphState) -> dict:
    """Load all three PDFs and extract raw text."""
    logger.info("=== Node: PDF Loader ===")
    errors: list[str] = list(state.get("errors", []))
    updates: dict[str, Any] = {}

    for key, path_key in [
        ("pdf1", "pdf1_path"),
        ("pdf2", "pdf2_path"),
        ("nepqa", "nepqa_path"),
    ]:
        path = state.get(path_key, "")
        if not path:
            errors.append(f"Path not provided for {path_key}")
            continue
        try:
            text, pages = load_pdf(path)
            updates[f"{key}_text"] = text
            if key != "nepqa":
                updates[f"{key}_pages"] = pages
        except Exception as e:
            msg = f"Failed to load {path}: {e}"
            logger.error(msg)
            errors.append(msg)

    updates["errors"] = errors
    return updates


# ---------------------------------------------------------------------------
# Node 2: Text Extraction Agent  (per-PDF)
# ---------------------------------------------------------------------------

def _extract_one(pdf_filename: str, pdf_path: str, pdf_text: str, page_count: int) -> ExtractedDocument:
    """Run extraction LLM for a single PDF."""
    human = EXTRACTION_HUMAN.format(
        pdf_filename=pdf_filename,
        pdf_text=_truncate(pdf_text),
    )
    try:
        data = _safe_llm_json(EXTRACTION_SYSTEM, human)
    except Exception as e:
        logger.error(f"Extraction LLM failed for {pdf_filename}: {e}")
        data = {}

    def _get(d: dict, *keys: str) -> Any:
        for k in keys:
            d = d.get(k, {}) if isinstance(d, dict) else {}
        return d

    product_raw = data.get("product", {})
    mfg_raw = data.get("manufacturer", {})
    specs_raw = data.get("technical_specs", {})
    label_raw = data.get("labeling", {})
    certs_raw = data.get("certifications", [])
    tests_raw = data.get("test_reports", [])

    def _nullify(d: dict) -> dict:
        return {k: (v if v not in ("", "N/A", "n/a", "None", "none") else None) for k, v in d.items()}

    product = ProductInfo(**_nullify(product_raw), source_pdf=pdf_filename, status=InfoStatus.UNVERIFIED)
    manufacturer = ManufacturerInfo(**_nullify(mfg_raw), source_pdf=pdf_filename, status=InfoStatus.UNVERIFIED)
    specs = TechnicalSpecs(**_nullify(specs_raw), source_pdf=pdf_filename, status=InfoStatus.UNVERIFIED)
    label = LabelingInfo(**_nullify(label_raw), source_pdf=pdf_filename, status=InfoStatus.UNVERIFIED)

    certs = [
        CertificationInfo(**_nullify(c), source_pdf=pdf_filename, status=InfoStatus.UNVERIFIED)
        for c in (certs_raw if isinstance(certs_raw, list) else [])
    ]
    tests = [
        TestReportInfo(**_nullify(t), source_pdf=pdf_filename, status=InfoStatus.UNVERIFIED)
        for t in (tests_raw if isinstance(tests_raw, list) else [])
    ]

    return ExtractedDocument(
        pdf_filename=pdf_filename,
        pdf_path=pdf_path,
        raw_text=pdf_text,
        page_count=page_count,
        product=product,
        manufacturer=manufacturer,
        technical_specs=specs,
        certifications=certs,
        test_reports=tests,
        labeling=label,
        safety_info=data.get("safety_info", []),
        additional_notes=data.get("additional_notes", []),
    )


def text_extraction_agent(state: GraphState) -> dict:
    """Extract structured data from both PDFs."""
    logger.info("=== Node: Text Extraction Agent ===")
    errors = list(state.get("errors", []))
    updates: dict[str, Any] = {}

    import os
    for key in ["pdf1", "pdf2"]:
        text = state.get(f"{key}_text", "")
        path = state.get(f"{key}_path", "")
        pages = state.get(f"{key}_pages", 0)
        filename = os.path.basename(path) if path else f"{key}.pdf"

        if not text:
            errors.append(f"No text available for {key}")
            continue

        try:
            extracted = _extract_one(filename, path, text, pages)
            updates[f"{key}_extracted"] = extracted
            logger.info(f"Extracted data from {filename}")
        except Exception as e:
            msg = f"Extraction failed for {key}: {traceback.format_exc()}"
            logger.error(msg)
            errors.append(msg)

    updates["errors"] = errors
    return updates


# ---------------------------------------------------------------------------
# Node 3: Data Normalization Agent
# ---------------------------------------------------------------------------

def data_normalization_agent(state: GraphState) -> dict:
    """Normalize extracted data (units, casing, whitespace)."""
    logger.info("=== Node: Data Normalization Agent ===")

    def _normalize_str(v: str | None) -> str | None:
        if not v:
            return v
        v = v.strip()
        # Normalize common variants
        replacements = {
            "N/A": None, "n/a": None, "not available": None,
            "Not Available": None, "unknown": None, "Unknown": None,
        }
        return replacements.get(v, v)

    def _normalize_specs(specs: TechnicalSpecs) -> TechnicalSpecs:
        d = specs.model_dump()
        for k, v in d.items():
            if isinstance(v, str):
                d[k] = _normalize_str(v)
        return TechnicalSpecs(**d)

    updates: dict[str, Any] = {}
    for key in ["pdf1_extracted", "pdf2_extracted"]:
        doc: ExtractedDocument | None = state.get(key)
        if doc is None:
            continue
        doc.technical_specs = _normalize_specs(doc.technical_specs)
        updates[key] = doc

    return updates


# ---------------------------------------------------------------------------
# Node 4: Reconciliation Agent
# ---------------------------------------------------------------------------

def reconciliation_agent(state: GraphState) -> dict:
    """Compare data across both PDFs and produce a reconciliation report."""
    logger.info("=== Node: Reconciliation Agent ===")
    errors = list(state.get("errors", []))

    doc1: ExtractedDocument | None = state.get("pdf1_extracted")
    doc2: ExtractedDocument | None = state.get("pdf2_extracted")

    if not doc1 or not doc2:
        errors.append("Cannot reconcile — one or both extracted docs missing")
        return {"errors": errors}

    import os
    pdf1_filename = os.path.basename(state.get("pdf1_path", "pdf1.pdf"))
    pdf2_filename = os.path.basename(state.get("pdf2_path", "pdf2.pdf"))

    pdf1_data = doc1.model_dump(exclude={"raw_text"})
    pdf2_data = doc2.model_dump(exclude={"raw_text"})

    human = RECONCILIATION_HUMAN.format(
        pdf1_filename=pdf1_filename,
        pdf1_data=json.dumps(pdf1_data, indent=2)[:6000],
        pdf2_filename=pdf2_filename,
        pdf2_data=json.dumps(pdf2_data, indent=2)[:6000],
    )

    try:
        data = _safe_llm_json(RECONCILIATION_SYSTEM, human)
    except Exception as e:
        logger.error(f"Reconciliation LLM failed: {e}")
        data = {}

    def _parse_comparisons(lst: list[dict]) -> list[FieldComparison]:
        results = []
        for item in (lst or []):
            try:
                results.append(FieldComparison(**item))
            except Exception:
                pass
        return results

    reconciliation = ReconciliationReport(
        exact_matches=_parse_comparisons(data.get("exact_matches", [])),
        partial_matches=_parse_comparisons(data.get("partial_matches", [])),
        conflicts=_parse_comparisons(data.get("conflicts", [])),
        only_in_pdf1=_parse_comparisons(data.get("only_in_pdf1", [])),
        only_in_pdf2=_parse_comparisons(data.get("only_in_pdf2", [])),
        missing_in_both=_parse_comparisons(data.get("missing_in_both", [])),
        overall_confidence=float(data.get("overall_confidence", 0.0)),
        summary=data.get("summary", ""),
    )

    logger.info(
        f"Reconciliation: {len(reconciliation.exact_matches)} exact, "
        f"{len(reconciliation.conflicts)} conflicts, "
        f"{len(reconciliation.missing_in_both)} missing"
    )
    return {"reconciliation": reconciliation, "errors": errors}


# ---------------------------------------------------------------------------
# Node 5: Compliance Mapping Agent
# ---------------------------------------------------------------------------

def compliance_mapping_agent(state: GraphState) -> dict:
    """Map available data to Nepal NEPQA 2025 import review sections."""
    logger.info("=== Node: Compliance Mapping Agent ===")
    errors = list(state.get("errors", []))

    nepqa_text = state.get("nepqa_text", "")
    doc1: ExtractedDocument | None = state.get("pdf1_extracted")
    doc2: ExtractedDocument | None = state.get("pdf2_extracted")
    reconciliation: ReconciliationReport | None = state.get("reconciliation")

    merged_data: dict = {}
    if doc1:
        merged_data["pdf1"] = doc1.model_dump(exclude={"raw_text"})
    if doc2:
        merged_data["pdf2"] = doc2.model_dump(exclude={"raw_text"})

    recon_summary = reconciliation.summary if reconciliation else "Reconciliation not available."

    human = COMPLIANCE_HUMAN.format(
        nepqa_context=_truncate(nepqa_text, 4000),
        merged_data=json.dumps(merged_data, indent=2)[:6000],
        reconciliation_summary=recon_summary,
    )

    try:
        data = _safe_llm_json(COMPLIANCE_SYSTEM, human)
    except Exception as e:
        logger.error(f"Compliance mapping LLM failed: {e}")
        data = {}

    sections = [
        NepalComplianceSection(**s)
        for s in (data.get("sections", []) or [])
        if isinstance(s, dict)
    ]

    nepal_compliance = NepalComplianceMap(
        sections=sections,
        supporting_docs_required=data.get("supporting_docs_required", []),
        supporting_docs_available=data.get("supporting_docs_available", []),
        overall_readiness=data.get("overall_readiness", ""),
    )

    logger.info(f"Compliance map: {len(sections)} sections evaluated")
    return {"nepal_compliance": nepal_compliance, "errors": errors}


# ---------------------------------------------------------------------------
# Node 6: Report Generation Agent
# ---------------------------------------------------------------------------

def report_generation_agent(state: GraphState) -> dict:
    """Generate the final Markdown report and ComplianceReport object."""
    logger.info("=== Node: Report Generation Agent ===")
    errors = list(state.get("errors", []))

    import os
    pdf1_filename = os.path.basename(state.get("pdf1_path", "pdf1.pdf"))
    pdf2_filename = os.path.basename(state.get("pdf2_path", "pdf2.pdf"))

    doc1: ExtractedDocument | None = state.get("pdf1_extracted")
    doc2: ExtractedDocument | None = state.get("pdf2_extracted")
    reconciliation: ReconciliationReport | None = state.get("reconciliation")
    nepal_compliance: NepalComplianceMap | None = state.get("nepal_compliance")

    product_model = "Unknown"
    if doc1 and doc1.product.product_model:
        product_model = doc1.product.product_model
    elif doc2 and doc2.product.product_model:
        product_model = doc2.product.product_model

    merged_data: dict = {}
    if doc1:
        merged_data["pdf1"] = doc1.model_dump(exclude={"raw_text"})
    if doc2:
        merged_data["pdf2"] = doc2.model_dump(exclude={"raw_text"})

    recon_summary = reconciliation.summary if reconciliation else "Not available."
    compliance_map_str = (
        json.dumps(nepal_compliance.model_dump(), indent=2)[:3000]
        if nepal_compliance else "Not available."
    )

    human = REPORT_HUMAN.format(
        product_model=product_model,
        pdf1_filename=pdf1_filename,
        pdf2_filename=pdf2_filename,
        merged_data=json.dumps(merged_data, indent=2)[:5000],
        reconciliation_summary=recon_summary,
        compliance_map=compliance_map_str,
    )

    llm = _get_llm(temperature=0.1)
    try:
        messages = [SystemMessage(content=REPORT_SYSTEM), HumanMessage(content=human)]
        response = llm.invoke(messages)
        report_markdown = response.content.strip()
    except Exception as e:
        logger.error(f"Report generation LLM failed: {e}")
        report_markdown = f"# Report Generation Failed\n\nError: {e}"
        errors.append(str(e))

    # Build ComplianceReport object
    product = doc1.product if doc1 else ProductInfo()
    manufacturer = doc1.manufacturer if doc1 else ManufacturerInfo()
    specs = doc1.technical_specs if doc1 else TechnicalSpecs()
    certs = (doc1.certifications if doc1 else []) + (doc2.certifications if doc2 else [])
    tests = (doc1.test_reports if doc1 else []) + (doc2.test_reports if doc2 else [])
    labeling = doc1.labeling if doc1 else LabelingInfo()
    safety = list(set((doc1.safety_info if doc1 else []) + (doc2.safety_info if doc2 else [])))

    compliance_report = ComplianceReport(
        pdf1_filename=pdf1_filename,
        pdf2_filename=pdf2_filename,
        product=product,
        manufacturer=manufacturer,
        technical_specs=specs,
        certifications=certs,
        test_reports=tests,
        labeling=labeling,
        safety_info=safety,
        reconciliation=reconciliation or ReconciliationReport(),
        nepal_compliance=nepal_compliance or NepalComplianceMap(),
        executive_summary="See full report markdown.",
    )

    logger.info("Report generation complete.")
    return {
        "report_markdown": report_markdown,
        "compliance_report": compliance_report,
        "errors": errors,
    }
