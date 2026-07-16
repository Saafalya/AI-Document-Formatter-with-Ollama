"""
formatting_css_loader.py
------------------------
Parses document_formatting.css for hardcoded visual formatting rules.
Font family, sizes, margins, and alignment are NOT extracted by AI —
they are defined here and applied deterministically to DOCX output.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
FORMATTING_CSS = BASE_DIR / "static" / "css" / "document_formatting.css"

# CSS custom property → internal formatting_rules key
_VAR_MAP = {
    "doc-font-family": "font_family",
    "doc-font-size": "font_size",
    "doc-alignment": "alignment",
    "doc-line-height": "line_spacing",
    "doc-paragraph-spacing-before": "paragraph_spacing_before",
    "doc-paragraph-spacing-after": "paragraph_spacing_after",
    "doc-heading-1-size": "heading1_size",
    "doc-heading-2-size": "heading2_size",
    "doc-heading-3-size": "heading3_size",
    "doc-heading-1-bold": "heading1_bold",
    "doc-heading-2-bold": "heading2_bold",
    "doc-heading-3-bold": "heading3_bold",
    "doc-margin-left": "margin_left",
    "doc-margin-right": "margin_right",
    "doc-margin-top": "margin_top",
    "doc-margin-bottom": "margin_bottom",
    "doc-avoid-all-caps": "avoid_all_caps",
    "doc-avoid-underline": "avoid_underline",
    "doc-avoid-excessive-bold": "avoid_excessive_bold",
    "doc-table-header-bold": "header_row_bold",
    "doc-table-border-style": "border_style",
}


def _parse_value(raw: str) -> Any:
    """Convert a CSS value string to a Python type for document_formatter."""
    raw = raw.strip().rstrip(";")
    lower = raw.lower()

    if lower in ("true", "false"):
        return lower == "true"

    if lower.endswith("pt"):
        try:
            return float(lower[:-2])
        except ValueError:
            return raw

    if lower.endswith("in"):
        try:
            return float(lower[:-2])
        except ValueError:
            return raw

    if lower.endswith("px"):
        try:
            return float(lower[:-2])
        except ValueError:
            return raw

    try:
        return float(raw)
    except ValueError:
        return raw.strip("'\"")


def load_formatting_from_css(css_path: Path = FORMATTING_CSS) -> Dict[str, Any]:
    """
    Parse CSS custom properties into a formatting_rules dict.

    Returns:
        Dict compatible with document_formatter.get_formatting_rules().
    """
    if not css_path.exists():
        logger.warning(f"Formatting CSS not found: {css_path}")
        return {}

    text = css_path.read_text(encoding="utf-8")
    formatting: Dict[str, Any] = {}
    table_rules: Dict[str, Any] = {}

    for match in re.finditer(r"--([\w-]+)\s*:\s*([^;]+);", text):
        var_name, raw_value = match.group(1), match.group(2)
        key = _VAR_MAP.get(var_name)
        if not key:
            continue
        value = _parse_value(raw_value)

        if var_name.startswith("doc-table-"):
            table_rules[key] = value
        else:
            formatting[key] = value

    logger.info(
        f"Loaded {len(formatting)} formatting rules from {css_path.name}"
    )
    return {"formatting_rules": formatting, "table_rules": table_rules}
