"""
compliance_checker.py
---------------------
Orchestrates the full compliance pipeline for a document.
Coordinates ViolationClassifier, StructureChecker, AIRewriter,
ChangeLogger, and produces a complete violations + changes report.
"""

import logging
from typing import Any, Dict, List

from modules.ai_rewriter import AIRewriter
from modules.change_logger import ChangeLogger
from modules.structure_checker import StructureChecker
from modules.violation_classifier import ViolationClassifier

logger = logging.getLogger(__name__)

# Violation → (category, severity, human-readable label)
VIOLATION_META: Dict[str, tuple] = {
    "passive_voice":              ("writing",    "warning", "Passive Voice"),
    "imperative_mood":            ("writing",    "info",    "Imperative Mood"),
    "inclusive_language":         ("writing",    "error",   "Non-Inclusive Language"),
    "terminology":                ("writing",    "warning", "Non-Preferred Terminology"),
    "readability":                ("writing",    "info",    "Readability Issue"),
    "font_mismatch":              ("formatting", "error",   "Font Mismatch"),
    "font_size_mismatch":         ("formatting", "error",   "Font Size Mismatch"),
    "alignment_mismatch":         ("formatting", "warning", "Alignment Mismatch"),
    "all_caps":                   ("formatting", "warning", "All Caps Usage"),
    "underline_usage":            ("formatting", "info",    "Underline Usage"),
    "excessive_bold":             ("formatting", "info",    "Excessive Bold"),
    "heading_formatting_mismatch":("formatting", "error",   "Heading Format Mismatch"),
    "heading_hierarchy":          ("structure",  "error",   "Heading Hierarchy Violation"),
    "missing_section":            ("structure",  "error",   "Missing Required Section"),
    "empty_heading":              ("structure",  "warning", "Empty Heading"),
    "consecutive_headings":       ("structure",  "warning", "Consecutive Headings"),
}


class ComplianceChecker:
    """Runs end-to-end compliance analysis and produces rewritten entries + violations."""

    def __init__(self):
        self.classifier = ViolationClassifier()
        self.structure_checker = StructureChecker()
        self.rewriter = AIRewriter()

    def run(
        self,
        analysis: Dict[str, Any],
        structure: List[Dict[str, Any]],
        change_logger: ChangeLogger,
        apply_rewrites: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute full compliance pipeline.

        Args:
            analysis: Output from DocumentAnalyser.analyse().
            structure: Output from StructureDetector.detect().
            change_logger: Shared ChangeLogger instance for this session.
            apply_rewrites: Whether to invoke the AI rewriter.

        Returns:
            Dict with: violations, rewritten_entries, violation_counts,
                       violation_by_severity, writing_violations, formatting_violations.
        """
        all_violations: List[Dict[str, Any]] = []
        rewritten_entries: List[Dict[str, Any]] = []

        # ── Structure violations ──────────────────────────────────────── #
        structure_violations = self.structure_checker.check(structure)
        for sv in structure_violations:
            meta = VIOLATION_META.get(sv["type"], ("structure", sv.get("severity", "warning"), sv["type"]))
            all_violations.append({
                **sv,
                "category": meta[0],
                "label": meta[2],
            })

        # ── Per-paragraph violations + rewrites ───────────────────────── #
        for entry in structure:
            if entry.get("is_empty"):
                continue

            violation_types = self.classifier.classify(entry)
            if not violation_types:
                rewritten_entries.append({**entry, "rewritten_text": entry["text"], "changed": False})
                continue

            # Record violations
            for vtype in violation_types:
                meta = VIOLATION_META.get(vtype, ("writing", "warning", vtype))
                all_violations.append({
                    "type": vtype,
                    "category": meta[0],
                    "severity": meta[1],
                    "label": meta[2],
                    "message": f"{meta[2]} detected in paragraph.",
                    "paragraph_index": entry["index"],
                    "section": entry["section"],
                    "original_text": entry["text"][:200],
                })

            # Rewrite if applicable
            new_text = entry["text"]
            changed = False
            writing_violations = [
                v for v in violation_types
                if VIOLATION_META.get(v, ("",))[0] == "writing"
            ]

            if apply_rewrites and writing_violations and entry["text"].strip():
                new_text, changed = self.rewriter.rewrite(
                    entry["text"],
                    writing_violations,
                    context=None,
                )
                if changed:
                    for vtype in writing_violations:
                        meta = VIOLATION_META.get(vtype, ("writing", "warning", vtype))
                        change_logger.log(
                            change_type=vtype,
                            category=meta[0],
                            before=entry["text"],
                            after=new_text,
                            section=entry["section"],
                            paragraph_index=entry["index"],
                            severity=meta[1],
                            rule_applied=meta[2],
                            accepted=True,
                        )
                        break  # One log entry per paragraph even if multiple violations

            rewritten_entries.append({
                **entry,
                "rewritten_text": new_text,
                "changed": changed,
                "violations": violation_types,
            })

        # ── Aggregate counts ──────────────────────────────────────────── #
        counts: Dict[str, int] = {}
        by_severity: Dict[str, int] = {"error": 0, "warning": 0, "info": 0}
        by_category: Dict[str, int] = {"writing": 0, "formatting": 0, "structure": 0}

        for v in all_violations:
            vtype = v["type"]
            counts[vtype] = counts.get(vtype, 0) + 1
            sev = v.get("severity", "warning")
            by_severity[sev] = by_severity.get(sev, 0) + 1
            cat = v.get("category", "writing")
            by_category[cat] = by_category.get(cat, 0) + 1

        logger.info(
            f"Compliance check complete: {len(all_violations)} violations, "
            f"{sum(1 for e in rewritten_entries if e.get('changed'))} rewrites."
        )

        return {
            "violations": all_violations,
            "rewritten_entries": rewritten_entries,
            "violation_counts": counts,
            "violation_by_severity": by_severity,
            "violation_by_category": by_category,
        }
