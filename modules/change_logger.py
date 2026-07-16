"""
change_logger.py
----------------
Centralized change log for the compliance pipeline.
Records every accepted or rejected rewrite and formatting change.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ChangeLogger:
    """Accumulates change records for a single compliance run."""

    def __init__(self):
        self._changes: List[Dict[str, Any]] = []

    def log(
        self,
        change_type: str,
        before: str,
        after: str,
        section: str = "",
        category: str = "writing",
        paragraph_index: int = -1,
        severity: str = "info",
        rule_applied: str = "",
        accepted: bool = True,
        reason: str = "",
    ) -> None:
        """
        Record a single change entry.

        Args:
            change_type: Violation or change type code (e.g. 'passive_voice').
            before: Original text.
            after: Rewritten or formatted text.
            section: Document section name.
            category: 'writing', 'formatting', or 'structure'.
            paragraph_index: Index in document paragraphs.
            severity: 'error', 'warning', or 'info'.
            rule_applied: Human-readable rule description.
            accepted: Whether the change was applied to the output.
            reason: Rejection reason if not accepted.
        """
        entry = {
            "type": change_type,
            "change_type": change_type,
            "before": before,
            "after": after,
            "section": section,
            "category": category,
            "paragraph_index": paragraph_index,
            "severity": severity,
            "rule_applied": rule_applied,
            "accepted": accepted,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._changes.append(entry)
        status = "accepted" if accepted else "rejected"
        logger.debug(f"Change logged [{status}] {change_type} in '{section[:30]}'")

    def get_all(self) -> List[Dict[str, Any]]:
        """Return all change records."""
        return list(self._changes)

    def get_accepted(self) -> List[Dict[str, Any]]:
        """Return only accepted changes."""
        return [c for c in self._changes if c.get("accepted")]

    def get_summary(self) -> Dict[str, Any]:
        """
        Aggregate change statistics.

        Returns:
            Dict with total_changes, accepted, rejected, by_category, by_type.
        """
        by_category: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        accepted = 0
        rejected = 0

        for c in self._changes:
            cat = c.get("category", "writing")
            by_category[cat] = by_category.get(cat, 0) + 1
            ctype = c.get("change_type", "unknown")
            by_type[ctype] = by_type.get(ctype, 0) + 1
            if c.get("accepted"):
                accepted += 1
            else:
                rejected += 1

        return {
            "total_changes": len(self._changes),
            "accepted": accepted,
            "rejected": rejected,
            "by_category": by_category,
            "by_type": by_type,
        }

    def clear(self) -> None:
        """Reset the change log."""
        self._changes.clear()
