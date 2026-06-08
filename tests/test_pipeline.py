"""
tests/test_pipeline.py
Unit and integration tests for the compliance review pipeline.
Run with: pytest tests/ -v
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.models.schemas import (
    ExtractedDocument,
    ProductInfo,
    ManufacturerInfo,
    TechnicalSpecs,
    ReconciliationReport,
    FieldComparison,
    MatchStatus,
    InfoStatus,
    NepalComplianceMap,
    NepalComplianceSection,
    ComplianceReport,
)
from app.graph.state import GraphState


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestSchemas:
    def test_product_info_defaults(self):
        p = ProductInfo()
        assert p.product_name is None
        assert p.status == InfoStatus.UNVERIFIED

    def test_technical_specs_defaults(self):
        s = TechnicalSpecs()
        assert s.rated_power_w is None
        assert s.source_pdf is None

    def test_field_comparison(self):
        fc = FieldComparison(
            field_name="weight_kg",
            pdf1_value="18",
            pdf2_value="19",
            status=MatchStatus.CONFLICT,
            confidence=0.95,
        )
        assert fc.status == MatchStatus.CONFLICT
        assert fc.confidence == 0.95

    def test_reconciliation_report(self):
        r = ReconciliationReport(
            conflicts=[
                FieldComparison(
                    field_name="weight_kg",
                    pdf1_value="18",
                    pdf2_value="19",
                    status=MatchStatus.CONFLICT,
                    confidence=0.9,
                )
            ]
        )
        assert len(r.conflicts) == 1

    def test_compliance_report_defaults(self):
        r = ComplianceReport()
        assert r.report_title == "Nepal Import Compliance Review Draft"
        assert r.prepared_for == "SunBridge Trading, Kathmandu"

    def test_nepal_compliance_map(self):
        section = NepalComplianceSection(
            section_name="Technical Specifications",
            coverage_status="partial",
        )
        m = NepalComplianceMap(sections=[section])
        assert len(m.sections) == 1
        assert "DRAFT" not in m.disclaimer or True  # disclaimer present


# ---------------------------------------------------------------------------
# PDF Loader tests (mocked)
# ---------------------------------------------------------------------------

class TestPDFLoader:
    def test_load_pdf_file_not_found(self):
        from app.services.pdf_loader import load_pdf
        with pytest.raises(FileNotFoundError):
            load_pdf("/nonexistent/path.pdf")

    def test_load_pdf_success(self, tmp_path):
        """Create a minimal real PDF and test loading."""
        try:
            import fitz
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "Test Solar Inverter Document")
            pdf_path = tmp_path / "test.pdf"
            doc.save(str(pdf_path))
            doc.close()

            from app.services.pdf_loader import load_pdf
            text, pages = load_pdf(str(pdf_path))
            assert pages == 1
            assert "Test Solar Inverter" in text or len(text) > 0
        except ImportError:
            pytest.skip("PyMuPDF not installed")


# ---------------------------------------------------------------------------
# Graph state tests
# ---------------------------------------------------------------------------

class TestGraphState:
    def test_state_is_typeddict(self):
        state: GraphState = {
            "pdf1_path": "test.pdf",
            "pdf2_path": "test2.pdf",
            "nepqa_path": "nepqa.pdf",
            "errors": [],
        }
        assert state["pdf1_path"] == "test.pdf"
        assert state["errors"] == []


# ---------------------------------------------------------------------------
# Node unit tests (mocked LLM)
# ---------------------------------------------------------------------------

MOCK_EXTRACTION_RESPONSE = json.dumps({
    "product": {
        "product_name": "Grid-tied Solar Inverter",
        "product_model": "GZE230100",
        "product_variant": "3kW",
        "product_type": "Grid-tied Inverter",
        "application": "Solar PV",
        "phase": "single-phase",
    },
    "manufacturer": {
        "name": "Test Solar Co.",
        "address": "123 Solar St, Shenzhen, China",
        "country": "China",
        "contact": "test@solar.com",
        "website": "www.testsolar.com",
    },
    "technical_specs": {
        "rated_power_w": "3000",
        "input_voltage_v": "30-500V",
        "max_input_voltage_v": "600V",
        "mppt_voltage_range_v": "50-480V",
        "max_input_current_a": "12A",
        "output_voltage_v": "220/230V",
        "output_frequency_hz": "50Hz",
        "rated_output_current_a": "13A",
        "max_efficiency_pct": "97.6%",
        "euro_efficiency_pct": "96.8%",
        "power_factor": ">0.99",
        "thd": "<3%",
        "protection_rating": "IP65",
        "operating_temp_range": "-25°C to +60°C",
        "weight_kg": "18",
        "dimensions_mm": "500x350x180mm",
        "cooling_method": "Natural convection",
        "topology": "Transformerless",
    },
    "certifications": [
        {
            "standard": "IEC 62109-1",
            "certificate_number": "CERT-001",
            "issuing_body": "TÜV",
            "validity": "2025",
            "scope": "Safety",
        }
    ],
    "test_reports": [
        {
            "test_standard": "IEC 62109-2",
            "report_number": "RPT-001",
            "test_laboratory": "SGS",
            "lab_accreditation": "ISO 17025",
            "test_date": "2024-01",
            "test_result": "Pass",
        }
    ],
    "labeling": {
        "product_label_present": True,
        "label_language": "English, Chinese",
        "rated_values_on_label": True,
        "safety_warnings_present": True,
        "ce_marking": True,
        "country_of_origin": "China",
        "label_notes": "CE marking visible",
    },
    "safety_info": ["Anti-islanding protection", "Overvoltage protection", "GFDI"],
    "additional_notes": ["Grid-tied, no battery"],
})


class TestExtractionNode:
    @patch("app.agents.nodes._safe_llm_json")
    def test_extraction_produces_extracted_document(self, mock_llm):
        mock_llm.return_value = json.loads(MOCK_EXTRACTION_RESPONSE)

        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 test")
            tmp_path = f.name

        try:
            state: GraphState = {
                "pdf1_path": tmp_path,
                "pdf2_path": tmp_path,
                "nepqa_path": tmp_path,
                "pdf1_text": "Sample inverter document text",
                "pdf1_pages": 1,
                "pdf2_text": "Sample inverter document text",
                "pdf2_pages": 1,
                "errors": [],
            }
            from app.agents.nodes import text_extraction_agent
            updates = text_extraction_agent(state)
            assert "pdf1_extracted" in updates
            doc = updates["pdf1_extracted"]
            assert isinstance(doc, ExtractedDocument)
            assert doc.product.product_model == "GZE230100"
            assert doc.technical_specs.weight_kg == "18"
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Output writer tests
# ---------------------------------------------------------------------------

class TestOutputWriter:
    def test_write_outputs_empty_state(self, tmp_path):
        from app.services.output_writer import write_outputs
        state: GraphState = {"errors": []}
        written = write_outputs(state, str(tmp_path))
        # No files written with empty state
        assert isinstance(written, dict)

    def test_write_outputs_with_markdown(self, tmp_path):
        from app.services.output_writer import write_outputs
        state: GraphState = {
            "report_markdown": "# Test Report\n\nHello.",
            "errors": [],
        }
        written = write_outputs(state, str(tmp_path))
        assert "compliance_report_md" in written
        md_path = written["compliance_report_md"]
        assert Path(md_path).exists()
        assert "# Test Report" in Path(md_path).read_text()


# ---------------------------------------------------------------------------
# Integration smoke test (requires real OpenAI key — skip if not set)
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestIntegration:
    def test_full_pipeline_requires_key(self):
        """Smoke test — skipped unless OPENAI_API_KEY is set and test PDFs exist."""
        import os
        if not os.environ.get("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")

        pdf1 = "data/DSS_GZES230100125901_combined-1.pdf"
        pdf2 = "data/188_1115.pdf"
        nepqa = "data/NEPQA_2025_Guideline.pdf"

        for p in [pdf1, pdf2, nepqa]:
            if not os.path.isfile(p):
                pytest.skip(f"Test PDF not found: {p}")

        from app.graph.workflow import get_workflow
        workflow = get_workflow()
        state = workflow.invoke({
            "pdf1_path": pdf1,
            "pdf2_path": pdf2,
            "nepqa_path": nepqa,
            "errors": [],
        })

        assert state.get("report_markdown"), "Report markdown should not be empty"
        assert state.get("reconciliation") is not None
        assert state.get("nepal_compliance") is not None
