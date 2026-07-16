"""
ai_rewriter.py
--------------
Centralized AI rewriting engine using local Ollama.
All text rewrites flow through this module.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from modules.ollama_client import get_ollama_client
from modules.rewrite_validator import RewriteValidator
from modules.rule_loader import get_inclusive_language_map, get_terminology_map

logger = logging.getLogger(__name__)


class AIRewriter:
    """Centralized rewriting engine with Ollama + rule-based fallbacks."""

    def __init__(self):
        self.ollama = get_ollama_client()
        self.validator = RewriteValidator()
        if not self.ollama.is_available():
            logger.warning(
                f"Ollama not available — AI rewrites disabled. "
                f"Start Ollama and run: ollama pull {self.ollama.model}"
            )

    def rewrite(
        self,
        text: str,
        violation_types: List[str],
        context: Optional[str] = None,
    ) -> Tuple[str, bool]:
        """
        Rewrite text to fix the specified violations.

        Returns:
            (rewritten_text, was_changed) tuple.
        """
        if not text or not text.strip():
            return text, False

        writing_violations = [
            v for v in violation_types
            if v in ("passive_voice", "imperative_mood", "inclusive_language",
                     "terminology", "readability")
        ]

        result = text
        result = self._apply_inclusive_language(result)
        result = self._apply_terminology(result)
        result = self._strip_please(result)

        remaining = [
            v for v in writing_violations
            if v in ("passive_voice", "readability")
        ]

        if remaining and self.ollama.is_available():
            ai_result = self._ai_rewrite(result, remaining, context)
            if ai_result and ai_result.strip() != result.strip():
                passed, reason = self.validator.validate(text, ai_result)
                if passed:
                    result = ai_result
                else:
                    logger.warning(f"AI rewrite rejected ({reason}): '{text[:60]}'")

        changed = result.strip() != text.strip()
        return result, changed

    def rewrite_batch(
        self, entries: List[Dict[str, Any]]
    ) -> List[Tuple[str, str, bool]]:
        results = []
        for entry in entries:
            original = entry.get("text", "")
            violations = entry.get("violations", [])
            rewritten, changed = self.rewrite(original, violations)
            results.append((original, rewritten, changed))
        return results

    def _apply_inclusive_language(self, text: str) -> str:
        mapping = get_inclusive_language_map()
        for term, replacement in mapping.items():
            pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
            text = pattern.sub(replacement, text)
        return text

    def _apply_terminology(self, text: str) -> str:
        mapping = get_terminology_map()
        for term, replacement in mapping.items():
            pattern = re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE)
            text = pattern.sub(replacement, text)
        return text

    def _strip_please(self, text: str) -> str:
        return re.sub(r"^\s*[Pp]lease\s+", "", text).capitalize() if text else text

    def _ai_rewrite(
        self,
        text: str,
        violations: List[str],
        context: Optional[str],
    ) -> Optional[str]:
        """Send text to Ollama for violation-specific rewriting."""
        instructions = self._build_instructions(violations)
        context_block = f"\nContext:\n{context[:500]}" if context else ""

        system = "You are a professional document editor. Return ONLY the rewritten sentence."

        prompt = f"""Rewrite this sentence to fix: {', '.join(violations)}.

Rules:
- Preserve numbers, dates, URLs, emails exactly
- Preserve named entities and technical terms
- Preserve meaning — minimal changes only
- Return ONLY the rewritten sentence, no quotes{context_block}

Instructions:
{instructions}

Original: {text}

Rewritten:"""

        result = self.ollama.chat(prompt, system=system, temperature=0.2, max_tokens=500)
        if result:
            return result.strip('"').strip("'").strip()
        return None

    def _build_instructions(self, violations: List[str]) -> str:
        mapping = {
            "passive_voice": "Convert passive to active voice.",
            "readability": "Remove filler words. Be direct and concise.",
            "imperative_mood": "Remove leading 'Please'.",
        }
        return "\n".join(f"• {mapping[v]}" for v in violations if v in mapping) or "• Improve clarity."
