"""
run_pipeline_test.py
--------------------
End-to-end pipeline test without starting the Flask server.
Run: python run_pipeline_test.py
"""

import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("pipeline_test")

BASE = Path(__file__).parent
TEST_DOCX = BASE / "test_data" / "sample_document.docx"
TEST_PDF = BASE / "test_data" / "style_guide.pdf"
OUTPUT_DIR = BASE / "outputs"


def main() -> int:
    if not TEST_DOCX.exists() or not TEST_PDF.exists():
        logger.error("Test files missing. Run: python test_data/create_test_files.py")
        return 1

    OUTPUT_DIR.mkdir(exist_ok=True)

    from modules.pipeline_runner import run_pipeline
    from modules.results_store import save_results

    logger.info("Running full compliance pipeline...")
    results = run_pipeline(
        str(TEST_DOCX),
        str(TEST_PDF),
        OUTPUT_DIR,
        run_id="test-run",
    )

    save_results(results["run_id"], results)

    summary = {
        "run_id": results["run_id"],
        "scores": results["scores"],
        "violation_counts": results["violation_counts"],
        "violation_by_category": results["violation_by_category"],
        "changes": len(results["changes"]),
        "output_docx": str(OUTPUT_DIR / results["output_filename"]),
        "report_pdf": str(OUTPUT_DIR / results["report_filename"]),
        "session_file": str(OUTPUT_DIR / "sessions" / f"{results['run_id']}.json"),
        "recommendations": [r["recommendation"][:80] for r in results["recommendations"][:5]],
    }

    summary_path = OUTPUT_DIR / "test_run_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    scores = results["scores"]
    print("\n" + "=" * 60)
    print("PIPELINE TEST COMPLETE")
    print("=" * 60)
    print(f"Overall Score:    {scores['overall_score']}% ({scores['grade']})")
    print(f"Writing:          {scores['writing_score']}%")
    print(f"Formatting:       {scores['formatting_score']}%")
    print(f"Structure:        {scores['structure_score']}%")
    print(f"Violations:       {len(results['violations'])}")
    print(f"Changes applied:  {results['change_summary']['accepted']}")
    print(f"Output DOCX:      {OUTPUT_DIR / results['output_filename']}")
    print(f"Report PDF:       {OUTPUT_DIR / results['report_filename']}")
    print(f"Session JSON:     {OUTPUT_DIR / 'sessions' / (results['run_id'] + '.json')}")
    print(f"Summary JSON:     {summary_path}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
