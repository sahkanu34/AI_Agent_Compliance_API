"""
models/schemas.py
All Pydantic v2 schemas for the Nepal compliance review system.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MatchStatus(str, Enum):
    EXACT = "exact_match"
    PARTIAL = "partial_match"
    CONFLICT = "conflict"
    ONLY_PDF1 = "only_in_pdf1"
    ONLY_PDF2 = "only_in_pdf2"
    MISSING = "missing_in_both"


class InfoStatus(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    MISSING = "missing"
    CONFLICTING = "conflicting"


# ---------------------------------------------------------------------------
# Core domain schemas
# ---------------------------------------------------------------------------

class ManufacturerInfo(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    country: Optional[str] = None
    contact: Optional[str] = None
    website: Optional[str] = None
    source_pdf: Optional[str] = None
    status: InfoStatus = InfoStatus.UNVERIFIED


class TechnicalSpecs(BaseModel):
    rated_power_w: Optional[str] = None
    input_voltage_v: Optional[str] = None
    max_input_voltage_v: Optional[str] = None
    mppt_voltage_range_v: Optional[str] = None
    max_input_current_a: Optional[str] = None
    output_voltage_v: Optional[str] = None
    output_frequency_hz: Optional[str] = None
    rated_output_current_a: Optional[str] = None
    max_efficiency_pct: Optional[str] = None
    euro_efficiency_pct: Optional[str] = None
    power_factor: Optional[str] = None
    thd: Optional[str] = None
    protection_rating: Optional[str] = None
    operating_temp_range: Optional[str] = None
    weight_kg: Optional[str] = None
    dimensions_mm: Optional[str] = None
    cooling_method: Optional[str] = None
    topology: Optional[str] = None
    source_pdf: Optional[str] = None
    status: InfoStatus = InfoStatus.UNVERIFIED


class CertificationInfo(BaseModel):
    standard: Optional[str] = None
    certificate_number: Optional[str] = None
    issuing_body: Optional[str] = None
    validity: Optional[str] = None
    scope: Optional[str] = None
    source_pdf: Optional[str] = None
    status: InfoStatus = InfoStatus.UNVERIFIED


class TestReportInfo(BaseModel):
    test_standard: Optional[str] = None
    report_number: Optional[str] = None
    test_laboratory: Optional[str] = None
    lab_accreditation: Optional[str] = None
    test_date: Optional[str] = None
    test_result: Optional[str] = None
    source_pdf: Optional[str] = None
    status: InfoStatus = InfoStatus.UNVERIFIED


class LabelingInfo(BaseModel):
    product_label_present: Optional[bool] = None
    label_language: Optional[str] = None
    rated_values_on_label: Optional[bool] = None
    safety_warnings_present: Optional[bool] = None
    ce_marking: Optional[bool] = None
    country_of_origin: Optional[str] = None
    label_notes: Optional[str] = None
    source_pdf: Optional[str] = None
    status: InfoStatus = InfoStatus.UNVERIFIED


class ProductInfo(BaseModel):
    product_name: Optional[str] = None
    product_model: Optional[str] = None
    product_variant: Optional[str] = None
    product_type: Optional[str] = None
    application: Optional[str] = None
    phase: Optional[str] = None
    source_pdf: Optional[str] = None
    status: InfoStatus = InfoStatus.UNVERIFIED


class ExtractedDocument(BaseModel):
    pdf_filename: str
    pdf_path: str
    raw_text: str = ""
    page_count: int = 0
    product: ProductInfo = Field(default_factory=ProductInfo)
    manufacturer: ManufacturerInfo = Field(default_factory=ManufacturerInfo)
    technical_specs: TechnicalSpecs = Field(default_factory=TechnicalSpecs)
    certifications: list[CertificationInfo] = Field(default_factory=list)
    test_reports: list[TestReportInfo] = Field(default_factory=list)
    labeling: LabelingInfo = Field(default_factory=LabelingInfo)
    safety_info: list[str] = Field(default_factory=list)
    additional_notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Reconciliation schemas
# ---------------------------------------------------------------------------

class FieldComparison(BaseModel):
    field_name: str
    pdf1_value: Optional[Any] = None
    pdf2_value: Optional[Any] = None
    status: MatchStatus = MatchStatus.MISSING
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    notes: Optional[str] = None


class ReconciliationReport(BaseModel):
    exact_matches: list[FieldComparison] = Field(default_factory=list)
    partial_matches: list[FieldComparison] = Field(default_factory=list)
    conflicts: list[FieldComparison] = Field(default_factory=list)
    only_in_pdf1: list[FieldComparison] = Field(default_factory=list)
    only_in_pdf2: list[FieldComparison] = Field(default_factory=list)
    missing_in_both: list[FieldComparison] = Field(default_factory=list)
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    summary: str = ""


# ---------------------------------------------------------------------------
# Nepal compliance mapping
# ---------------------------------------------------------------------------

class NepalComplianceSection(BaseModel):
    section_name: str
    nepqa_reference: Optional[str] = None
    coverage_status: str  # "covered" | "partial" | "missing"
    available_info: Optional[str] = None
    gaps: Optional[str] = None
    recommendation: Optional[str] = None


class NepalComplianceMap(BaseModel):
    sections: list[NepalComplianceSection] = Field(default_factory=list)
    supporting_docs_required: list[str] = Field(default_factory=list)
    supporting_docs_available: list[str] = Field(default_factory=list)
    overall_readiness: str = ""
    disclaimer: str = (
        "This mapping is based solely on information present in the supplied manufacturer "
        "PDFs, cross-referenced against NEPQA 2025 as an import-side reference. No compliance "
        "claims are made. Final determination rests with the Nepal authority."
    )


# ---------------------------------------------------------------------------
# Final report schema
# ---------------------------------------------------------------------------

class ComplianceReport(BaseModel):
    report_title: str = "Nepal Import Compliance Review Draft"
    prepared_for: str = "SunBridge Trading, Kathmandu"
    prepared_by: str = "Cantordust AI Engineer — Automated Review System"
    report_version: str = "DRAFT v1.0"

    # Core data
    pdf1_filename: str = ""
    pdf2_filename: str = ""
    product: ProductInfo = Field(default_factory=ProductInfo)
    manufacturer: ManufacturerInfo = Field(default_factory=ManufacturerInfo)
    technical_specs: TechnicalSpecs = Field(default_factory=TechnicalSpecs)
    certifications: list[CertificationInfo] = Field(default_factory=list)
    test_reports: list[TestReportInfo] = Field(default_factory=list)
    labeling: LabelingInfo = Field(default_factory=LabelingInfo)
    safety_info: list[str] = Field(default_factory=list)

    # Analysis
    reconciliation: ReconciliationReport = Field(default_factory=ReconciliationReport)
    nepal_compliance: NepalComplianceMap = Field(default_factory=NepalComplianceMap)

    # Report sections (markdown text)
    executive_summary: str = ""
    recommendations: list[str] = Field(default_factory=list)
    appendix_notes: list[str] = Field(default_factory=list)
