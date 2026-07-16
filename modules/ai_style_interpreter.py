"""
ai_style_interpreter.py
-----------------------
Uses local Ollama to extract SEMANTIC rules from style guide PDF text.
Visual formatting (font, size, margins) is defined in document_formatting.css
and is NOT extracted by AI.
"""

import json
import logging
import re
from typing import Any, Dict

from modules.ollama_client import get_ollama_client

logger = logging.getLogger(__name__)

# AI extracts semantic rules only — formatting lives in CSS
SEMANTIC_SCHEMA = {
    "writing_rules": [],
    "structure_rules": {},
    "branding_rules": {},
    "image_rules": {},
    "inclusive_language_map": {},
    "terminology_map": {},
}


class AIStyleInterpreter:
    """Extracts semantic compliance rules from style guide text using Ollama."""

    def __init__(self):
        self.ollama = get_ollama_client()
        if self.ollama.is_available():
            models = self.ollama.list_models()
            logger.info(
                f"Ollama ready. Model: {self.ollama.model}. Installed: {models[:5]}"
            )
        else:
            logger.warning(
                f"Ollama not reachable at {self.ollama.base_url}. "
                f"Run: ollama pull {self.ollama.model}"
            )

    def extract_rules(self, guide_text: str) -> Dict[str, Any]:
        """
        Extract semantic rules from style guide text.

        Args:
            guide_text: Plain text from the style guide PDF.

        Returns:
            Dict with writing, structure, branding, language maps.
            Does NOT include formatting_rules (see document_formatting.css).
        """
        if not guide_text or not guide_text.strip():
            logger.warning("Empty style guide text — returning empty semantic rules.")
            return self._empty_result()

        if self.ollama.is_available():
            ai_result = self._extract_with_ollama(guide_text)
            if ai_result:
                return ai_result

        return self._extract_heuristic(guide_text)

    def _extract_with_ollama(self, guide_text: str) -> Dict[str, Any]:
        """Use Ollama to extract semantic rules as JSON."""
        truncated = guide_text[:10000]

        system = (
            "You are a corporate document governance expert. "
            "Return ONLY valid JSON. No markdown, no explanation."
        )

        prompt = f"""Analyse this style guide and extract SEMANTIC rules only.
Do NOT extract font names, font sizes, or margins — those are configured separately.

Return JSON with this exact structure:
{{
  "writing_rules": ["rule about voice, tone, clarity..."],
  "structure_rules": {{
    "heading_hierarchy": true,
    "required_sections": ["section names"],
    "max_heading_depth": 3
  }},
  "branding_rules": {{
    "company_name": "string or null",
    "primary_color": "string or null"
  }},
  "image_rules": {{
    "caption_required": true
  }},
  "inclusive_language_map": {{"old_term": "preferred_term"}},
  "terminology_map": {{"discouraged_term": "preferred_term"}}
}}

Style guide text:
{truncated}"""

        raw = self.ollama.chat(prompt, system=system, temperature=0.1, max_tokens=2000)
        if not raw:
            return {}

        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        raw = re.sub(r"\s*```$", "", raw)

        try:
            parsed = json.loads(raw)
            logger.info("Ollama semantic rule extraction successful.")
            return self._normalise(parsed)
        except json.JSONDecodeError as e:
            logger.error(f"Ollama returned invalid JSON: {e}")
            return {}

    def _extract_heuristic(self, guide_text: str) -> Dict[str, Any]:
        """Fallback keyword extraction when Ollama is unavailable."""
        logger.info("Using heuristic semantic rule extraction.")
        result = self._empty_result()
        lower = guide_text.lower()

        if "active voice" in lower:
            result["writing_rules"].append("Use active voice instead of passive voice.")
        if "inclusive" in lower:
            result["writing_rules"].append("Use inclusive language throughout.")
        if "please" in lower and ("avoid" in lower or "do not" in lower):
            result["writing_rules"].append("Do not begin instructions with 'Please'.")

        sections = re.findall(
            r"(?:required\s+sections?|must\s+include)[:\s]+([^\n.]+)",
            guide_text,
            re.IGNORECASE,
        )
        if sections:
            names = [s.strip() for s in re.split(r"[,;]", sections[0]) if s.strip()]
            result["structure_rules"]["required_sections"] = names

        if "heading hierarchy" in lower or "do not skip" in lower:
            result["structure_rules"]["heading_hierarchy"] = True

        for old, new in [
            ("chairman", "chairperson"),
            ("manpower", "workforce"),
            ("utilize", "use"),
            ("leverage", "use"),
        ]:
            if old in lower:
                key = (
                    "inclusive_language_map"
                    if old in ("chairman", "manpower")
                    else "terminology_map"
                )
                result[key][old] = new

        return result

    def _normalise(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        result = self._empty_result()
        for key in result:
            if key in parsed and parsed[key]:
                result[key] = parsed[key]
        return result

    def _empty_result(self) -> Dict[str, Any]:
        return {
            k: (v.copy() if isinstance(v, dict) else list(v))
            for k, v in SEMANTIC_SCHEMA.items()
        }
