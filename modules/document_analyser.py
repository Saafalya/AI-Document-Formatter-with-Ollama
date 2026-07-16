"""
document_analyser.py
--------------------
Reads a DOCX file and extracts a structured representation of all content
(headings, paragraphs, tables, images) with formatting metadata.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

logger = logging.getLogger(__name__)

ALIGNMENT_MAP = {
    WD_ALIGN_PARAGRAPH.LEFT: "left",
    WD_ALIGN_PARAGRAPH.CENTER: "center",
    WD_ALIGN_PARAGRAPH.RIGHT: "right",
    WD_ALIGN_PARAGRAPH.JUSTIFY: "justify",
    None: "left",
}


class DocumentAnalyser:
    """Parses a DOCX and returns a structured content + formatting inventory."""

    def __init__(self, docx_path: str):
        self.docx_path = Path(docx_path)
        if not self.docx_path.exists():
            raise FileNotFoundError(f"Document not found: {docx_path}")
        self.doc = Document(str(self.docx_path))
        logger.info(f"Loaded document: {self.docx_path.name}")

    def analyse(self) -> Dict[str, Any]:
        """
        Full document analysis.

        Returns:
            Dict with keys: structure, paragraphs, tables, images, metadata.
        """
        structure = self._extract_structure()
        tables = self._extract_tables()
        images = self._count_images()
        metadata = self._extract_metadata()

        return {
            "structure": structure,
            "tables": tables,
            "images": images,
            "metadata": metadata,
            "paragraph_count": len([s for s in structure if s["type"] == "paragraph"]),
            "heading_count": len([s for s in structure if s["type"] == "heading"]),
        }

    def _extract_structure(self) -> List[Dict[str, Any]]:
        """Extract all paragraphs and headings with full formatting details."""
        structure = []
        current_section = "Introduction"

        for idx, para in enumerate(self.doc.paragraphs):
            text = para.text.strip()
            style_name = para.style.name if para.style else "Normal"
            is_heading = style_name.startswith("Heading")

            # Track current section name
            if is_heading:
                current_section = text or current_section

            level = 0
            if is_heading:
                try:
                    level = int(style_name.split()[-1])
                except ValueError:
                    level = 1

            entry = {
                "index": idx,
                "type": "heading" if is_heading else "paragraph",
                "text": text,
                "style": style_name,
                "level": level,
                "section": current_section,
                "formatting": self._get_para_formatting(para),
                "runs": self._get_runs(para),
                "is_list": self._is_list_item(para),
            }
            structure.append(entry)

        logger.debug(f"Extracted {len(structure)} paragraphs/headings.")
        return structure

    def _get_para_formatting(self, para) -> Dict[str, Any]:
        """Extract paragraph-level formatting."""
        pf = para.paragraph_format
        fmt = {
            "alignment": ALIGNMENT_MAP.get(para.alignment, "left"),
            "space_before": pf.space_before.pt if pf.space_before else None,
            "space_after": pf.space_after.pt if pf.space_after else None,
            "line_spacing": None,
        }
        if pf.line_spacing:
            try:
                fmt["line_spacing"] = float(pf.line_spacing)
            except Exception:
                fmt["line_spacing"] = None
        return fmt

    def _get_runs(self, para) -> List[Dict[str, Any]]:
        """Extract per-run formatting for the first run (representative sample)."""
        runs = []
        for run in para.runs:
            font = run.font
            run_data = {
                "text": run.text,
                "bold": run.bold,
                "italic": run.italic,
                "underline": run.underline,
                "font_name": font.name,
                "font_size": font.size.pt if font.size else None,
                "all_caps": font.all_caps,
            }
            runs.append(run_data)
        return runs

    def _is_list_item(self, para) -> bool:
        """Detect whether a paragraph is a list/bullet item."""
        style_name = para.style.name.lower() if para.style else ""
        if "list" in style_name or "bullet" in style_name:
            return True
        pPr = para._p.find(qn("w:pPr"))
        if pPr is not None:
            numPr = pPr.find(qn("w:numPr"))
            return numPr is not None
        return False

    def _extract_tables(self) -> List[Dict[str, Any]]:
        """Extract table metadata."""
        tables = []
        for i, table in enumerate(self.doc.tables):
            rows = len(table.rows)
            cols = len(table.columns)
            header_text = ""
            if rows > 0:
                header_text = " | ".join(
                    cell.text.strip() for cell in table.rows[0].cells
                )
            tables.append({
                "index": i,
                "rows": rows,
                "columns": cols,
                "header": header_text,
            })
        return tables

    def _count_images(self) -> int:
        """Count inline images in the document."""
        count = 0
        for rel in self.doc.part.rels.values():
            if "image" in rel.reltype:
                count += 1
        return count

    def _extract_metadata(self) -> Dict[str, Any]:
        """Extract document core properties."""
        props = self.doc.core_properties
        return {
            "title": props.title or "",
            "author": props.author or "",
            "created": str(props.created) if props.created else "",
            "modified": str(props.modified) if props.modified else "",
            "word_count": sum(
                len(p.text.split()) for p in self.doc.paragraphs if p.text.strip()
            ),
        }
