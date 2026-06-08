"""
app/services/pdf_loader.py
Loads PDFs using PyMuPDF + pdfplumber for robust text extraction.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import pdfplumber

from app.utils.logger import get_logger

logger = get_logger(__name__)


def extract_text_pymupdf(pdf_path: str) -> tuple[str, int]:
    """Extract full text and page count via PyMuPDF."""
    doc = fitz.open(pdf_path)
    pages: list[str] = []
    for page in doc:
        pages.append(page.get_text("text"))
    doc.close()
    return "\n".join(pages), len(pages)


def extract_text_pdfplumber(pdf_path: str) -> str:
    """Fallback extraction via pdfplumber (handles some edge cases better)."""
    parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
            # Also attempt table extraction
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    parts.append(" | ".join(str(c or "") for c in row))
    return "\n".join(parts)


def load_pdf(pdf_path: str) -> tuple[str, int]:
    """
    Load a PDF and return (combined_text, page_count).
    Merges PyMuPDF + pdfplumber output for maximum coverage.
    """
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    logger.info(f"Loading PDF: {Path(pdf_path).name}")

    text_mudf, page_count = extract_text_pymupdf(pdf_path)
    text_plumber = extract_text_pdfplumber(pdf_path)

    # Combine — prefer longer extraction
    combined = text_mudf if len(text_mudf) >= len(text_plumber) else text_plumber
    # Append any extra content from the other extractor
    if text_mudf != text_plumber:
        # Deduplicate by lines
        lines_main = set(combined.splitlines())
        extra_lines = [
            l for l in (text_plumber if combined == text_mudf else text_mudf).splitlines()
            if l.strip() and l not in lines_main
        ]
        if extra_lines:
            combined += "\n" + "\n".join(extra_lines)

    logger.info(
        f"Extracted {page_count} pages, {len(combined)} chars from {Path(pdf_path).name}"
    )
    return combined, page_count
