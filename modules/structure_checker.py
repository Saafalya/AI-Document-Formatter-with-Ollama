"""
structure_checker.py
--------------------
Validates document structure against style guide structure rules.
Detects heading hierarchy violations, missing required sections,
and incorrect section ordering.
"""

import logging
from typing import Any, Dict, List

from modules.rule_loader import get_structure_rules

logger = logging.getLogger(__name__)


class StructureChecker:
    """Checks structural compliance of a document against structure rules."""

    def check(self, structure: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Run all structure checks and return a list of violations.

        Args:
            structure: Output from StructureDetector.detect().

        Returns:
            List of violation dicts with keys: type, severity, message,
            paragraph_index, section.
        """
        rules = get_structure_rules()
        violations = []

        violations.extend(self._check_heading_hierarchy(structure, rules))
        violations.extend(self._check_required_sections(structure, rules))
        violations.extend(self._check_empty_headings(structure))
        violations.extend(self._check_consecutive_headings(structure))

        logger.info(f"Structure check found {len(violations)} violations.")
        return violations

    def _check_heading_hierarchy(
        self, structure: List[Dict[str, Any]], rules: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect skipped heading levels (e.g., H1 → H3 without H2)."""
        if not rules.get("heading_hierarchy", True):
            return []

        violations = []
        headings = [e for e in structure if e["type"] == "heading" and e["level"] > 0]
        prev_level = 0

        for h in headings:
            level = h["level"]
            if level > prev_level + 1 and prev_level > 0:
                violations.append({
                    "type": "heading_hierarchy",
                    "severity": "error",
                    "message": (
                        f"Heading level skipped: H{prev_level} → H{level} "
                        f"('{h['text'][:60]}'). Expected H{prev_level + 1}."
                    ),
                    "paragraph_index": h["index"],
                    "section": h["section"],
                })
            prev_level = level

        return violations

    def _check_required_sections(
        self, structure: List[Dict[str, Any]], rules: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Check that all required sections exist in the document."""
        required = rules.get("required_sections", [])
        if not required:
            return []

        existing = {
            e["text"].strip().lower()
            for e in structure
            if e["type"] == "heading"
        }

        violations = []
        for section in required:
            if section.lower() not in existing:
                violations.append({
                    "type": "missing_section",
                    "severity": "error",
                    "message": f"Required section '{section}' is missing from the document.",
                    "paragraph_index": -1,
                    "section": "Document",
                })
        return violations

    def _check_empty_headings(self, structure: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Flag headings with no text content."""
        violations = []
        for e in structure:
            if e["type"] == "heading" and e.get("is_empty"):
                violations.append({
                    "type": "empty_heading",
                    "severity": "warning",
                    "message": "Empty heading detected.",
                    "paragraph_index": e["index"],
                    "section": e["section"],
                })
        return violations

    def _check_consecutive_headings(
        self, structure: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Flag two headings in a row with no content between them."""
        violations = []
        prev_was_heading = False

        for e in structure:
            if e["type"] == "heading":
                if prev_was_heading:
                    violations.append({
                        "type": "consecutive_headings",
                        "severity": "warning",
                        "message": (
                            f"Consecutive headings without content: '{e['text'][:60]}'"
                        ),
                        "paragraph_index": e["index"],
                        "section": e["section"],
                    })
                prev_was_heading = True
            elif e["type"] == "paragraph" and not e.get("is_empty"):
                prev_was_heading = False

        return violations
