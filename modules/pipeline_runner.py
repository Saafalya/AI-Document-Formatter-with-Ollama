"""
pipeline_runner.py
------------------
Shared compliance pipeline used by the Flask app and CLI test runner.
"""

import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from modules.ai_style_interpreter import AIStyleInterpreter
from modules.change_logger import ChangeLogger
from modules.compliance_checker import ComplianceChecker
from modules.compliance_report import ComplianceReportGenerator
from modules.compliance_score import ComplianceScorer
from modules.document_analyser import DocumentAnalyser
from modules.document_formatter import DocumentFormatter
from modules.recommendation_engine import RecommendationEngine
from modules.rule_loader import merge_ai_rules
from modules.structure_detector import StructureDetector
from modules.styleguide_parser import StyleGuideParser

logger = logging.getLogger(__name__)


def build_preview(entries, max_entries: int = 80) -> list:
    """Build lightweight preview data from rewritten entries."""
    preview = []
    for e in entries[:max_entries]:
        if not e.get("text", "").strip():
            continue
        preview.append({
            "index": e["index"],
            "type": e["type"],
            "level": e.get("level", 0),
            "original": e["text"][:800],
            "rewritten": e.get("rewritten_text", e["text"])[:800],
            "changed": e.get("changed", False),
            "violations": e.get("violations", []),
            "section": e.get("section", ""),
        })
    return preview


def run_pipeline(
    docx_path: str,
    pdf_path: str,
    output_dir: Path,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute the full compliance pipeline.

    Args:
        docx_path: Path to uploaded DOCX.
        pdf_path: Path to style guide PDF.
        output_dir: Directory for formatted DOCX and PDF report.
        run_id: Optional run identifier (generated if omitted).

    Returns:
        Complete results dict ready for results_store.save_results().
    """
    run_id = run_id or uuid.uuid4().hex[:8]
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / f"formatted_{run_id}.docx"

    logger.info("Step 1: Parsing style guide PDF...")
    parser = StyleGuideParser(pdf_path)
    guide_text = parser.extract_full_text()

    logger.info("Step 2: Extracting rules with AI...")
    interpreter = AIStyleInterpreter()
    ai_rules = interpreter.extract_rules(guide_text)
    merged_rules = merge_ai_rules(ai_rules)

    logger.info("Step 3: Analysing document structure...")
    analyser = DocumentAnalyser(docx_path)
    analysis = analyser.analyse()

    detector = StructureDetector()
    structure = detector.detect(analysis)

    logger.info("Step 4-6: Running compliance checks and rewrites...")
    change_logger = ChangeLogger()
    checker = ComplianceChecker()
    compliance = checker.run(analysis, structure, change_logger, apply_rewrites=True)

    logger.info("Step 7: Scoring compliance...")
    scorer = ComplianceScorer()
    scores = scorer.score(compliance["violations"], analysis["paragraph_count"])

    engine = RecommendationEngine()
    recommendations = engine.generate(compliance["violations"], scores)

    logger.info("Step 8: Formatting document...")
    formatter = DocumentFormatter(docx_path, str(output_path))
    formatter.apply_all(compliance["rewritten_entries"], change_logger)

    report_path = output_dir / f"report_{run_id}.pdf"
    report_gen = ComplianceReportGenerator(str(report_path))
    report_gen.generate(
        scores=scores,
        violations=compliance["violations"],
        recommendations=recommendations,
        changes=change_logger.get_all(),
        metadata=analysis["metadata"],
        run_id=run_id,
    )

    return {
        "run_id": run_id,
        "output_filename": output_path.name,
        "report_filename": report_path.name,
        "docx_upload": Path(docx_path).name,
        "pdf_upload": Path(pdf_path).name,
        "scores": scores,
        "violations": compliance["violations"],
        "violation_counts": compliance["violation_counts"],
        "violation_by_severity": compliance["violation_by_severity"],
        "violation_by_category": compliance["violation_by_category"],
        "recommendations": recommendations,
        "changes": change_logger.get_all(),
        "change_summary": change_logger.get_summary(),
        "extracted_rules": {
            "formatting": merged_rules.get("formatting_rules", {}),
            "formatting_source": merged_rules.get("formatting_source", "static/css/document_formatting.css"),
            "writing": merged_rules.get("writing_rules", []),
            "structure": merged_rules.get("structure_rules", {}),
            "writing_source": "Ollama AI + style_rules.json",
        },
        "metadata": analysis["metadata"],
        "preview": build_preview(compliance["rewritten_entries"]),
    }
