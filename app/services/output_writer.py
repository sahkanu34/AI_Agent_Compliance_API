"""
app/services/output_writer.py
Saves extracted_data.json, comparison_report.json, compliance_report.md
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from app.graph.state import GraphState
from app.utils.logger import get_logger

logger = get_logger(__name__)


def write_outputs(state: GraphState, output_dir: str = "outputs") -> dict[str, str]:
    """
    Write all output files and return a dict of {label: filepath}.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    written: dict[str, str] = {}

    # --- extracted_data.json ---
    extracted: dict[str, object] = {}
    for key in ["pdf1_extracted", "pdf2_extracted"]:
        doc = state.get(key)
        if doc:
            extracted[key] = doc.model_dump(exclude={"raw_text"})
    if extracted:
        path = os.path.join(output_dir, "extracted_data.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(extracted, f, indent=2, default=str)
        written["extracted_data"] = path
        logger.info(f"Written: {path}")

    # --- comparison_report.json ---
    reconciliation = state.get("reconciliation")
    nepal_compliance = state.get("nepal_compliance")
    comparison: dict[str, object] = {}
    if reconciliation:
        comparison["reconciliation"] = reconciliation.model_dump()
    if nepal_compliance:
        comparison["nepal_compliance"] = nepal_compliance.model_dump()
    if comparison:
        path = os.path.join(output_dir, "comparison_report.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(comparison, f, indent=2, default=str)
        written["comparison_report"] = path
        logger.info(f"Written: {path}")

    # --- compliance_report.md ---
    report_md = state.get("report_markdown", "")
    if report_md:
        path = os.path.join(output_dir, "compliance_report.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(report_md)
        written["compliance_report_md"] = path
        logger.info(f"Written: {path}")

    # --- full_compliance_report.json ---
    full_report = state.get("compliance_report")
    if full_report:
        path = os.path.join(output_dir, "full_compliance_report.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(full_report.model_dump(exclude={"reconciliation", "nepal_compliance"}), f, indent=2, default=str)
        written["full_compliance_report"] = path
        logger.info(f"Written: {path}")

    return written
