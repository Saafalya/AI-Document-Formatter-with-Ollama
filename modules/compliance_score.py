"""
compliance_score.py
-------------------
Calculates weighted compliance scores across formatting, writing,
and structure dimensions. Returns a breakdown and overall score.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Severity weights for score deduction
SEVERITY_WEIGHTS = {"error": 5, "warning": 2, "info": 1}

# Category → max deduction cap (prevents one bad section killing the whole score)
CATEGORY_CAP = {"writing": 50, "formatting": 40, "structure": 30}


class ComplianceScorer:
    """Computes compliance scores from violation data."""

    def score(
        self,
        violations: List[Dict[str, Any]],
        total_paragraphs: int,
    ) -> Dict[str, Any]:
        """
        Calculate per-category and overall compliance scores.

        Args:
            violations: List of violation dicts from ComplianceChecker.
            total_paragraphs: Total paragraph count for normalisation.

        Returns:
            Dict with formatting_score, writing_score, structure_score, overall_score,
            and grade (A–F).
        """
        if total_paragraphs == 0:
            return self._perfect_score()

        deductions: Dict[str, float] = {"writing": 0, "formatting": 0, "structure": 0}

        for v in violations:
            cat = v.get("category", "writing")
            sev = v.get("severity", "warning")
            weight = SEVERITY_WEIGHTS.get(sev, 2)
            if cat in deductions:
                deductions[cat] += weight

        # Normalise deductions relative to document size
        scale = max(total_paragraphs, 10)
        scores = {}
        for cat, deduction in deductions.items():
            cap = CATEGORY_CAP[cat]
            normalised = min(deduction / scale * 10, cap)
            scores[f"{cat}_score"] = round(max(0, 100 - normalised))

        # Weighted overall score
        weights = {"writing_score": 0.45, "formatting_score": 0.35, "structure_score": 0.20}
        overall = sum(scores.get(k, 100) * w for k, w in weights.items())
        scores["overall_score"] = round(overall)
        scores["grade"] = self._grade(scores["overall_score"])

        logger.info(
            f"Compliance scores: formatting={scores.get('formatting_score')}, "
            f"writing={scores.get('writing_score')}, "
            f"structure={scores.get('structure_score')}, "
            f"overall={scores['overall_score']} ({scores['grade']})"
        )
        return scores

    @staticmethod
    def _grade(score: int) -> str:
        if score >= 95:  return "A+"
        if score >= 90:  return "A"
        if score >= 85:  return "B+"
        if score >= 80:  return "B"
        if score >= 70:  return "C"
        if score >= 60:  return "D"
        return "F"

    @staticmethod
    def _perfect_score() -> Dict[str, Any]:
        return {
            "formatting_score": 100,
            "writing_score": 100,
            "structure_score": 100,
            "overall_score": 100,
            "grade": "A+",
        }
