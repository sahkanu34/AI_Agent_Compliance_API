#!/usr/bin/env python3
"""
run_review.py
CLI entrypoint — run compliance review directly without API server.

Now automatically loads ALL PDFs from the data/ folder.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.graph.workflow import get_workflow
from app.services.output_writer import write_outputs
from app.utils.logger import get_logger

logger = get_logger("run_review")


def main() -> None:
    parser = argparse.ArgumentParser(description="Nepal Compliance Review CLI")
    parser.add_argument(
        "--data_dir",
        default="data",
        help="Directory containing all PDFs (default: data/)",
    )
    parser.add_argument(
        "--output",
        default="outputs",
        help="Output directory (default: outputs/)",
    )

    args = parser.parse_args()

    data_path = Path(args.data_dir)

    if not data_path.exists():
        logger.error(f"Data directory not found: {data_path}")
        sys.exit(1)

    # Collect all PDFs
    all_pdfs = sorted(data_path.glob("*.pdf"))

    if not all_pdfs:
        logger.error("No PDF files found in data folder")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("Cantordust Nepal Compliance Review — Starting")
    logger.info("=" * 60)

    logger.info(f"Data folder : {data_path}")
    logger.info(f"Output      : {args.output}")
    logger.info(f"PDF count   : {len(all_pdfs)}")

    for pdf in all_pdfs:
        logger.info(f"  - {pdf.name}")

    logger.info("=" * 60)

    # Try to identify NEPQA file (optional logic)
    nepqa_files = [p for p in all_pdfs if "nepqa" in p.name.lower()]
    nepqa_path = str(nepqa_files[0]) if nepqa_files else None

    # Manufacturer PDFs = everything except NEPQA
    manufacturer_pdfs = [
        str(p) for p in all_pdfs if str(p) != nepqa_path
    ] if nepqa_path else [str(p) for p in all_pdfs]

    logger.info(f"NEPQA file  : {nepqa_path if nepqa_path else 'NOT FOUND'}")
    logger.info(f"Input PDFs  : {len(manufacturer_pdfs)}")

    workflow = get_workflow()

    initial_state = {
        "pdf_paths": manufacturer_pdfs,
        "nepqa_path": nepqa_path,
        "errors": [],
    }

    final_state = workflow.invoke(initial_state)

    errors = final_state.get("errors", [])
    if errors:
        logger.warning(f"{len(errors)} error(s) encountered:")
        for e in errors:
            logger.warning(f"  - {e}")

    written = write_outputs(final_state, args.output)

    logger.info("=" * 60)
    logger.info("Output files written:")

    for label, path in written.items():
        logger.info(f"  {label}: {path}")

    reconciliation = final_state.get("reconciliation")
    if reconciliation:
        logger.info("")
        logger.info("Reconciliation Summary:")
        logger.info(f"  Exact matches   : {len(reconciliation.exact_matches)}")
        logger.info(f"  Partial matches : {len(reconciliation.partial_matches)}")
        logger.info(f"  Conflicts       : {len(reconciliation.conflicts)}")
        logger.info(f"  Missing in both : {len(reconciliation.missing_in_both)}")
        logger.info(f"  Confidence      : {reconciliation.overall_confidence:.2f}")

    logger.info("=" * 60)
    logger.info("Done.")


if __name__ == "__main__":
    main()