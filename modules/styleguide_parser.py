"""
styleguide_parser.py
--------------------
Extracts raw text and tables from a style guide PDF using pdfplumber.
Provides the text input for AI rule extraction.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

import pdfplumber

logger = logging.getLogger(__name__)


class StyleGuideParser:
    """Parses a style guide PDF and extracts structured text content."""

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"Style guide PDF not found: {pdf_path}")
        logger.info(f"StyleGuideParser initialised: {self.pdf_path.name}")

    def extract_full_text(self) -> str:
        """
        Extract all text from every page of the PDF.

        Returns:
            Concatenated plain text from all pages.
        """
        pages_text: List[str] = []

        with pdfplumber.open(str(self.pdf_path)) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages_text.append(f"--- Page {i + 1} ---\n{text}")

        full_text = "\n\n".join(pages_text)
        logger.info(
            f"Extracted {len(full_text)} characters from "
            f"{len(pages_text)} pages of {self.pdf_path.name}"
        )
        return full_text

    def extract_tables(self) -> List[List[List[str]]]:
        """
        Extract all tables from the PDF.

        Returns:
            List of tables, each table being a list of rows (list of cell strings).
        """
        all_tables: List[List[List[str]]] = []

        with pdfplumber.open(str(self.pdf_path)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables() or []
                for table in tables:
                    cleaned = [
                        [cell or "" for cell in row]
                        for row in table
                        if row
                    ]
                    if cleaned:
                        all_tables.append(cleaned)

        logger.debug(f"Extracted {len(all_tables)} tables from PDF.")
        return all_tables

    def get_metadata(self) -> Dict[str, Any]:
        """Return basic PDF metadata."""
        with pdfplumber.open(str(self.pdf_path)) as pdf:
            return {
                "page_count": len(pdf.pages),
                "filename": self.pdf_path.name,
                "file_size_kb": round(self.pdf_path.stat().st_size / 1024, 1),
            }
