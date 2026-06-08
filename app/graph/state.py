"""
app/graph/state.py
TypedDict state shared across all LangGraph nodes.
"""
from __future__ import annotations

from typing import Any, Optional
from typing_extensions import TypedDict

from app.models.schemas import (
    ExtractedDocument,
    ReconciliationReport,
    NepalComplianceMap,
    ComplianceReport,
)


class GraphState(TypedDict, total=False):
    # Input
    pdf1_path: str
    pdf2_path: str
    nepqa_path: str

    # After PDF loading
    pdf1_text: str
    pdf1_pages: int
    pdf2_text: str
    pdf2_pages: int
    nepqa_text: str

    # After extraction
    pdf1_extracted: ExtractedDocument
    pdf2_extracted: ExtractedDocument

    # After reconciliation
    reconciliation: ReconciliationReport

    # After Nepal compliance mapping
    nepal_compliance: NepalComplianceMap

    # After report generation
    report_markdown: str
    compliance_report: ComplianceReport

    # Error tracking
    errors: list[str]
