"""
recommendation_engine.py
------------------------
Generates prioritised, actionable recommendations from compliance results.
Recommendations are deduplicated, ordered by severity and frequency,
and mapped to specific document locations.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Maps violation type → recommendation template
RECOMMENDATION_TEMPLATES: Dict[str, str] = {
    "passive_voice": (
        "Convert passive voice to active voice throughout. "
        "Example: 'The report was approved by management' → 'Management approved the report'."
    ),
    "imperative_mood": (
        "Remove 'Please' from instructional sentences. "
        "Style guides prefer direct imperatives: 'Click the button' not 'Please click the button'."
    ),
    "inclusive_language": (
        "Replace non-inclusive terms with preferred alternatives. "
        "Review the inclusive language map in your style guide for the full substitution list."
    ),
    "terminology": (
        "Replace discouraged jargon with preferred terminology. "
        "Consistent vocabulary improves document clarity and brand alignment."
    ),
    "readability": (
        "Remove filler words (very, basically, actually, quite, really, just). "
        "Direct language improves reader engagement and document professionalism."
    ),
    "font_mismatch": (
        "Standardise font family across the document. "
        "Ensure all body text uses the organisation's approved font."
    ),
    "font_size_mismatch": (
        "Correct font sizes to match style guide specifications. "
        "Consistent sizing maintains document hierarchy and readability."
    ),
    "alignment_mismatch": (
        "Apply consistent paragraph alignment as required by the style guide."
    ),
    "all_caps": (
        "Avoid ALL CAPS text. Use sentence case or title case instead. "
        "All-caps text reduces readability and is considered aggressive in formal documents."
    ),
    "underline_usage": (
        "Reserve underline for hyperlinks only. "
        "Use bold or italics for emphasis in running text."
    ),
    "excessive_bold": (
        "Reduce bold usage to only critical terms. "
        "Overuse of bold dilutes emphasis and reduces visual hierarchy."
    ),
    "heading_formatting_mismatch": (
        "Apply correct heading sizes as defined in the style guide. "
        "Consistent heading formatting maintains document structure."
    ),
    "heading_hierarchy": (
        "Maintain a logical heading hierarchy without skipping levels. "
        "Do not jump from H1 to H3 without an H2 — this breaks document navigation."
    ),
    "missing_section": (
        "Add all required sections as specified in the style guide. "
        "Missing sections may violate document compliance requirements."
    ),
    "empty_heading": (
        "Remove or populate empty headings. "
        "Empty headings create navigation issues and look unprofessional."
    ),
    "consecutive_headings": (
        "Add content between consecutive headings. "
        "Two headings without intervening content suggests structural issues."
    ),
}

SEVERITY_ORDER = {
    "error": 0,
    "warning": 1,
    "info": 2,
}


class RecommendationEngine:
    """Generates a prioritised recommendation list from violation data."""

    def generate(
        self,
        violations: List[Dict[str, Any]],
        scores: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Produce prioritised, deduplicated recommendations.

        Args:
            violations: List of violation dicts from ComplianceChecker.
            scores: Score dict from ComplianceScorer.

        Returns:
            List of recommendation dicts ordered by priority.
        """
        # Count violations by type and track worst severity seen
        type_counts: Dict[str, int] = {}
        type_severity: Dict[str, str] = {}

        for v in violations:
            vtype = v["type"]
            type_counts[vtype] = type_counts.get(vtype, 0) + 1
            current_sev = type_severity.get(vtype, "info")
            new_sev = v.get("severity", "info")
            if SEVERITY_ORDER.get(new_sev, 2) < SEVERITY_ORDER.get(current_sev, 2):
                type_severity[vtype] = new_sev

        # Build recommendation entries
        recommendations = []
        for vtype, count in type_counts.items():
            template = RECOMMENDATION_TEMPLATES.get(vtype)
            if not template:
                continue
            severity = type_severity.get(vtype, "info")
            recommendations.append(
                {
                    "violation_type": vtype,
                    "severity": severity,
                    "count": count,
                    "recommendation": template,
                    "priority": SEVERITY_ORDER.get(severity, 2),
                }
            )

        # Sort by severity then frequency
        recommendations.sort(key=lambda r: (r["priority"], -r["count"]))

        # Add score-based global recommendations
        if scores.get("overall_score", 100) < 70:
            recommendations.insert(
                0,
                {
                    "violation_type": "general",
                    "severity": "error",
                    "count": 0,
                    "recommendation": (
                        "This document requires significant revision before it meets compliance standards. "
                        f"Current overall score: {scores.get('overall_score')}%. "
                        "Address all error-level violations first."
                    ),
                    "priority": -1,
                },
            )

        logger.info(f"Generated {len(recommendations)} recommendations.")
        return recommendations
