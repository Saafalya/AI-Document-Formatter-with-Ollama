"""
violation_classifier.py
-----------------------
Centralized violation classifier. Accepts a paragraph entry and returns
all violation types it contains. Used by compliance_checker as the single
classification authority — no other module performs violation detection logic.
"""

import logging
import re
from typing import Any, Dict, List

from modules.rule_loader import get_formatting_rules, get_inclusive_language_map, get_terminology_map

logger = logging.getLogger(__name__)

# Passive voice patterns (common auxiliary + past participle signals)
_PASSIVE_PATTERNS = [
    re.compile(r"\b(was|were|is|are|been|be|being)\s+\w+ed\b", re.IGNORECASE),
    re.compile(r"\b(was|were|is|are|been|be|being)\s+\w+en\b", re.IGNORECASE),
]

# Filler / weak language patterns
_FILLER_PATTERNS = re.compile(
    r"\b(very|quite|rather|somewhat|basically|actually|literally|"
    r"really|just|simply|generally|usually|often|hopefully)\b",
    re.IGNORECASE,
)

# Imperative mood check: starts with "please" before a verb
_PLEASE_PATTERN = re.compile(r"^\s*please\s+\w", re.IGNORECASE)


class ViolationClassifier:
    """Classifies all violation types present in a single paragraph."""

    def classify(self, entry: Dict[str, Any]) -> List[str]:
        """
        Determine which violation categories apply to this paragraph entry.

        Args:
            entry: A structure entry dict from StructureDetector / DocumentAnalyser,
                   must contain 'text', 'runs', 'formatting', 'type'.

        Returns:
            List of violation type strings (may be empty).
        """
        text = entry.get("text", "").strip()
        if not text or entry.get("type") == "heading":
            # Headings are handled by structure checker; skip here
            return self._classify_heading_formatting(entry)

        violations: List[str] = []

        # Writing violations
        if self._has_passive_voice(text):
            violations.append("passive_voice")
        if self._has_please_imperative(text):
            violations.append("imperative_mood")
        if self._has_inclusive_language_issues(text):
            violations.append("inclusive_language")
        if self._has_terminology_issues(text):
            violations.append("terminology")
        if self._has_filler_words(text):
            violations.append("readability")

        # Formatting violations (from run data)
        fmt_violations = self._classify_run_formatting(entry)
        violations.extend(fmt_violations)

        return violations

    # ------------------------------------------------------------------ #
    # Writing checks                                                       #
    # ------------------------------------------------------------------ #

    def _has_passive_voice(self, text: str) -> bool:
        return any(p.search(text) for p in _PASSIVE_PATTERNS)

    def _has_please_imperative(self, text: str) -> bool:
        return bool(_PLEASE_PATTERN.match(text))

    def _has_inclusive_language_issues(self, text: str) -> bool:
        lower = text.lower()
        return any(term in lower for term in get_inclusive_language_map())

    def _has_terminology_issues(self, text: str) -> bool:
        lower = text.lower()
        return any(term in lower for term in get_terminology_map())

    def _has_filler_words(self, text: str) -> bool:
        return bool(_FILLER_PATTERNS.search(text))

    # ------------------------------------------------------------------ #
    # Formatting checks                                                    #
    # ------------------------------------------------------------------ #

    def _classify_run_formatting(self, entry: Dict[str, Any]) -> List[str]:
        """Check run-level formatting against style rules."""
        rules = get_formatting_rules()
        runs = entry.get("runs", [])
        violations: List[str] = []

        if not runs:
            return violations

        # Use first run as representative
        first_run = runs[0]
        expected_font = rules.get("font_family")
        expected_size = rules.get("font_size")

        if expected_font and first_run.get("font_name"):
            if first_run["font_name"].lower() != expected_font.lower():
                violations.append("font_mismatch")

        if expected_size and first_run.get("font_size"):
            if abs(first_run["font_size"] - expected_size) > 0.5:
                violations.append("font_size_mismatch")

        # All caps check
        if rules.get("avoid_all_caps") and first_run.get("all_caps"):
            violations.append("all_caps")

        # Underline check
        if rules.get("avoid_underline") and first_run.get("underline"):
            violations.append("underline_usage")

        # Excessive bold: bold text in non-heading paragraphs
        bold_runs = sum(1 for r in runs if r.get("bold") and r.get("text", "").strip())
        if rules.get("avoid_excessive_bold") and bold_runs > 3:
            violations.append("excessive_bold")

        # Alignment check
        expected_align = rules.get("alignment", "left")
        para_align = entry.get("formatting", {}).get("alignment", "left")
        if para_align and para_align != expected_align:
            violations.append("alignment_mismatch")

        return violations

    def _classify_heading_formatting(self, entry: Dict[str, Any]) -> List[str]:
        """Heading-specific formatting checks."""
        if entry.get("type") != "heading":
            return []
        rules = get_formatting_rules()
        violations: List[str] = []
        runs = entry.get("runs", [])
        if not runs:
            return violations

        level = entry.get("level", 1)
        size_key = f"heading{level}_size"
        expected_size = rules.get(size_key)
        actual_size = runs[0].get("font_size")

        if expected_size and actual_size:
            if abs(actual_size - expected_size) > 0.5:
                violations.append("heading_formatting_mismatch")

        text = entry.get("text", "")
        if rules.get("avoid_all_caps") and text == text.upper() and text.isalpha():
            violations.append("all_caps")

        return violations
