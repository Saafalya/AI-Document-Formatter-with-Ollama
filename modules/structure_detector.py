"""
structure_detector.py
---------------------
Detects and classifies the logical document structure from analysed content.
Produces a clean structure list used by the structure checker and compliance engine.
"""

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class StructureDetector:
    """Converts raw document analysis into a clean structural hierarchy."""

    def detect(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Build a structural map from document analysis output.

        Args:
            analysis: Output from DocumentAnalyser.analyse().

        Returns:
            List of structure entries with type, text, level, section.
        """
        structure = []
        for item in analysis.get("structure", []):
            entry = {
                "index": item["index"],
                "type": item["type"],
                "text": item["text"],
                "level": item.get("level", 0),
                "section": item.get("section", ""),
                "style": item.get("style", "Normal"),
                "formatting": item.get("formatting", {}),
                "runs": item.get("runs", []),
                "is_list": item.get("is_list", False),
                "word_count": len(item["text"].split()) if item["text"] else 0,
                "char_count": len(item["text"]),
                "is_empty": not bool(item["text"].strip()),
            }
            structure.append(entry)

        headings = [e for e in structure if e["type"] == "heading"]
        logger.info(
            f"Structure detected: {len(structure)} elements, "
            f"{len(headings)} headings."
        )
        return structure

    def get_heading_outline(self, structure: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract just the heading hierarchy for outline display."""
        return [e for e in structure if e["type"] == "heading"]

    def get_section_names(self, structure: List[Dict[str, Any]]) -> List[str]:
        """Return unique top-level (H1) section names."""
        return [
            e["text"] for e in structure
            if e["type"] == "heading" and e["level"] == 1 and e["text"]
        ]

    def get_paragraphs_in_section(
        self, structure: List[Dict[str, Any]], section_name: str
    ) -> List[Dict[str, Any]]:
        """Return all paragraph entries belonging to a named section."""
        result = []
        in_section = False
        for entry in structure:
            if entry["type"] == "heading" and entry["level"] == 1:
                in_section = entry["text"] == section_name
            if in_section and entry["type"] == "paragraph":
                result.append(entry)
        return result
