"""
rule_loader.py
--------------
Central rule store.

- Visual formatting (font, size, margins) → static/css/document_formatting.css
- Semantic rules (voice, terminology, structure) → style_rules.json + Ollama AI
"""

import json
import logging
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules.formatting_css_loader import load_formatting_from_css

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
RULES_FILE = BASE_DIR / "style_rules.json"

_cached_rules: Optional[Dict[str, Any]] = None

# Keys the AI may enrich — NOT formatting (that lives in CSS)
SEMANTIC_KEYS = (
    "writing_rules",
    "structure_rules",
    "branding_rules",
    "image_rules",
    "inclusive_language_map",
    "terminology_map",
)


def load_rules(force_reload: bool = False) -> Dict[str, Any]:
    """
    Load combined rule set: CSS formatting + JSON semantic rules.

    Returns:
        Dict with formatting_rules, writing_rules, structure_rules, etc.
    """
    global _cached_rules
    if _cached_rules is not None and not force_reload:
        return _cached_rules

    css_data = load_formatting_from_css()
    semantic = _load_semantic_json()

    _cached_rules = {
        "formatting_rules": css_data.get("formatting_rules", {}),
        "table_rules": {**semantic.get("table_rules", {}), **css_data.get("table_rules", {})},
        "writing_rules": semantic.get("writing_rules", []),
        "structure_rules": semantic.get("structure_rules", {}),
        "branding_rules": semantic.get("branding_rules", {}),
        "image_rules": semantic.get("image_rules", {}),
        "inclusive_language_map": semantic.get("inclusive_language_map", {}),
        "terminology_map": semantic.get("terminology_map", {}),
        "formatting_source": "static/css/document_formatting.css",
    }

    logger.info("Rules loaded: formatting from CSS, semantics from JSON/AI.")
    return _cached_rules


def _load_semantic_json() -> Dict[str, Any]:
    """Load semantic-only rules from style_rules.json."""
    if not RULES_FILE.exists():
        return _empty_semantic()
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Strip legacy formatting if still present in JSON
    data.pop("formatting_rules", None)
    return data


def save_rules(rules: Dict[str, Any]) -> None:
    """Persist semantic rules to style_rules.json (not formatting CSS)."""
    global _cached_rules
    semantic = {k: rules[k] for k in (
        "writing_rules", "structure_rules", "branding_rules",
        "table_rules", "image_rules",
        "inclusive_language_map", "terminology_map",
    ) if k in rules}
    with open(RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(semantic, f, indent=2)
    load_rules(force_reload=True)
    logger.info("Semantic rules saved to style_rules.json")


def merge_ai_rules(ai_rules: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge AI-extracted SEMANTIC rules only.
    Formatting is never overridden by AI — it comes from document_formatting.css.

    Args:
        ai_rules: Output from AIStyleInterpreter.extract_rules().

    Returns:
        Merged rule dict.
    """
    base = deepcopy(load_rules())

    for key in ("structure_rules", "branding_rules", "image_rules"):
        if key in ai_rules and isinstance(ai_rules[key], dict):
            base.setdefault(key, {})
            for k, v in ai_rules[key].items():
                if v is not None and v != "":
                    base[key][k] = v

    if "writing_rules" in ai_rules and ai_rules["writing_rules"]:
        existing = set(base.get("writing_rules", []))
        for rule in ai_rules["writing_rules"]:
            if rule and rule not in existing:
                base.setdefault("writing_rules", []).append(rule)

    for map_key in ("inclusive_language_map", "terminology_map"):
        if map_key in ai_rules and isinstance(ai_rules[map_key], dict):
            base.setdefault(map_key, {})
            base[map_key].update(ai_rules[map_key])

    global _cached_rules
    _cached_rules = base
    logger.info("AI semantic rules merged (formatting unchanged from CSS).")
    return base


def get_formatting_rules() -> Dict[str, Any]:
    """Return formatting_rules from CSS."""
    return load_rules().get("formatting_rules", {})


def get_structure_rules() -> Dict[str, Any]:
    return load_rules().get("structure_rules", {})


def get_inclusive_language_map() -> Dict[str, str]:
    return load_rules().get("inclusive_language_map", {})


def get_terminology_map() -> Dict[str, str]:
    return load_rules().get("terminology_map", {})


def get_writing_rules() -> List[str]:
    return load_rules().get("writing_rules", [])


def _empty_semantic() -> Dict[str, Any]:
    return {
        "writing_rules": [],
        "structure_rules": {},
        "branding_rules": {},
        "table_rules": {},
        "image_rules": {},
        "inclusive_language_map": {},
        "terminology_map": {},
    }
