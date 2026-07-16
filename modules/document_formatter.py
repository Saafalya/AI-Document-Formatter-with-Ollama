"""
document_formatter.py
---------------------
Applies formatting rules from the style guide to a DOCX document in-place.
Modifies font, size, spacing, alignment, and heading styles using python-docx.
Generates the final compliant output document.
"""

import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from modules.rule_loader import get_formatting_rules
from modules.change_logger import ChangeLogger

logger = logging.getLogger(__name__)

ALIGNMENT_LOOKUP = {
    "left":    WD_ALIGN_PARAGRAPH.LEFT,
    "center":  WD_ALIGN_PARAGRAPH.CENTER,
    "right":   WD_ALIGN_PARAGRAPH.RIGHT,
    "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
}


class DocumentFormatter:
    """Applies style guide formatting rules to a DOCX document."""

    def __init__(self, source_path: str, output_path: str):
        """
        Args:
            source_path: Path to the original DOCX.
            output_path: Path to write the formatted DOCX.
        """
        self.source_path = Path(source_path)
        self.output_path = Path(output_path)
        shutil.copy2(self.source_path, self.output_path)
        self.doc = Document(str(self.output_path))
        self.rules = get_formatting_rules()
        logger.info(f"DocumentFormatter ready: {self.source_path.name} → {self.output_path.name}")

    def apply_all(
        self,
        rewritten_entries: List[Dict[str, Any]],
        change_logger: ChangeLogger,
    ) -> str:
        """
        Apply all formatting rules and text rewrites to the output document.

        Args:
            rewritten_entries: List of paragraph entries with 'rewritten_text' and 'changed'.
            change_logger: Shared ChangeLogger for this session.

        Returns:
            Absolute path to the saved output DOCX.
        """
        self._apply_document_defaults()
        self._apply_paragraph_formatting(rewritten_entries, change_logger)
        self._apply_table_formatting()

        self.doc.save(str(self.output_path))
        logger.info(f"Formatted document saved: {self.output_path}")
        return str(self.output_path)

    def _apply_document_defaults(self) -> None:
        """Set document-level defaults: margins, default font, default size."""
        from docx.shared import Inches
        for section in self.doc.sections:
            margin = self.rules.get("margin_left", 1.25)
            section.left_margin = Inches(self.rules.get("margin_left", 1.25))
            section.right_margin = Inches(self.rules.get("margin_right", 1.25))
            section.top_margin = Inches(self.rules.get("margin_top", 1.0))
            section.bottom_margin = Inches(self.rules.get("margin_bottom", 1.0))
        logger.debug("Document margins applied.")

    def _apply_paragraph_formatting(
        self,
        rewritten_entries: List[Dict[str, Any]],
        change_logger: ChangeLogger,
    ) -> None:
        """Apply per-paragraph formatting and inject rewritten text."""
        entry_map = {e["index"]: e for e in rewritten_entries}

        for idx, para in enumerate(self.doc.paragraphs):
            entry = entry_map.get(idx)
            style_name = para.style.name if para.style else "Normal"
            is_heading = style_name.startswith("Heading")

            # Apply rewritten text if changed
            if entry and entry.get("changed") and entry.get("rewritten_text"):
                original = para.text
                new_text = entry["rewritten_text"]
                if original != new_text and para.runs:
                    # Preserve formatting of first run, replace text
                    first_run = para.runs[0]
                    first_run.text = new_text
                    # Clear subsequent runs to avoid duplication
                    for run in para.runs[1:]:
                        run.text = ""

            # Apply heading formatting
            if is_heading:
                self._format_heading(para, style_name)
            else:
                self._format_body_paragraph(para)

    def _format_heading(self, para, style_name: str) -> None:
        """Apply heading-specific font size and weight rules."""
        try:
            level = int(style_name.split()[-1])
        except (ValueError, IndexError):
            level = 1

        size_key = f"heading{level}_size"
        bold_key = f"heading{level}_bold"
        font_size = self.rules.get(size_key, 14)
        is_bold = self.rules.get(bold_key, True)
        font_family = self.rules.get("font_family", "Calibri")

        for run in para.runs:
            if font_family:
                run.font.name = font_family
            run.font.size = Pt(font_size)
            run.bold = is_bold

    def _format_body_paragraph(self, para) -> None:
        """Apply body paragraph formatting rules."""
        font_family = self.rules.get("font_family", "Calibri")
        font_size = self.rules.get("font_size", 11)
        alignment = self.rules.get("alignment", "left")
        space_before = self.rules.get("paragraph_spacing_before", 6)
        space_after = self.rules.get("paragraph_spacing_after", 6)

        if alignment in ALIGNMENT_LOOKUP:
            para.alignment = ALIGNMENT_LOOKUP[alignment]

        pf = para.paragraph_format
        if space_before is not None:
            pf.space_before = Pt(space_before)
        if space_after is not None:
            pf.space_after = Pt(space_after)

        for run in para.runs:
            if font_family:
                run.font.name = font_family
            if font_size:
                run.font.size = Pt(font_size)

    def _apply_table_formatting(self) -> None:
        """Apply table header bold and basic border styles."""
        from modules.rule_loader import load_rules
        table_rules = load_rules().get("table_rules", {})
        header_bold = table_rules.get("header_row_bold", True)

        for table in self.doc.tables:
            if not table.rows:
                continue
            if header_bold:
                for cell in table.rows[0].cells:
                    for para in cell.paragraphs:
                        for run in para.runs:
                            run.bold = True

        logger.debug(f"Table formatting applied to {len(self.doc.tables)} tables.")
