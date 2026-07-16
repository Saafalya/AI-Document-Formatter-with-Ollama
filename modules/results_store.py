"""
results_store.py
----------------
Persists compliance run results to disk instead of the Flask session cookie.
Flask signed cookies are limited to ~4 KB; full results can be 10–50+ KB.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path(__file__).parent.parent / "outputs" / "sessions"


def _ensure_dir() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def save_results(run_id: str, results: Dict[str, Any]) -> str:
    """
    Save a full results dict to disk.

    Args:
        run_id: Unique run identifier.
        results: Complete results payload.

    Returns:
        Absolute path to the saved JSON file.
    """
    _ensure_dir()
    path = SESSIONS_DIR / f"{run_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False)
    logger.info(f"Results saved: {path.name} ({path.stat().st_size // 1024} KB)")
    return str(path)


def load_results(run_id: str) -> Optional[Dict[str, Any]]:
    """
    Load results for a run_id.

    Returns:
        Results dict or None if not found.
    """
    if not run_id:
        return None
    path = SESSIONS_DIR / f"{run_id}.json"
    if not path.exists():
        logger.warning(f"Results not found for run_id={run_id}")
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_summary(run_id: str) -> Optional[Dict[str, Any]]:
    """Return a lightweight summary for the navbar (no full payload)."""
    results = load_results(run_id)
    if not results:
        return None
    return {
        "run_id": run_id,
        "output_filename": results.get("output_filename", ""),
        "report_filename": results.get("report_filename", ""),
        "overall_score": results.get("scores", {}).get("overall_score", 0),
        "grade": results.get("scores", {}).get("grade", ""),
    }
