"""
compliance_report.py
--------------------
Generates a PDF compliance report using ReportLab.
Includes scores, violation summary, recommendations, and change log.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)


class ComplianceReportGenerator:
    """Builds a downloadable PDF compliance report."""

    def __init__(self, output_path: str):
        self.output_path = Path(output_path)

    def generate(
        self,
        scores: Dict[str, Any],
        violations: List[Dict[str, Any]],
        recommendations: List[Dict[str, Any]],
        changes: List[Dict[str, Any]],
        metadata: Dict[str, Any],
        run_id: str = "",
    ) -> str:
        """
        Generate the compliance report PDF.

        Args:
            scores: Output from ComplianceScorer.
            violations: List of violation dicts.
            recommendations: List of recommendation dicts.
            changes: List of change log entries.
            metadata: Document metadata dict.
            run_id: Unique run identifier.

        Returns:
            Absolute path to the generated PDF.
        """
        doc = SimpleDocTemplate(
            str(self.output_path),
            pagesize=A4,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Heading1"],
            fontSize=20,
            spaceAfter=12,
            textColor=colors.HexColor("#1e3a5f"),
        )
        heading_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontSize=14,
            spaceBefore=16,
            spaceAfter=8,
            textColor=colors.HexColor("#2c5282"),
        )
        body_style = ParagraphStyle(
            "ReportBody",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
        )

        story = []

        story.append(Paragraph("AI Document Formatter — Compliance Report", title_style))
        story.append(
            Paragraph(
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Run ID: {run_id}",
                body_style,
            )
        )
        if metadata.get("title"):
            story.append(Paragraph(f"Document: {metadata['title']}", body_style))
        story.append(Paragraph(f"Word count: {metadata.get('word_count', 'N/A')}", body_style))
        story.append(Spacer(1, 0.25 * inch))

        # Scores table
        story.append(Paragraph("Compliance Scores", heading_style))
        score_data = [
            ["Category", "Score"],
            ["Overall", f"{scores.get('overall_score', 0)}% ({scores.get('grade', 'N/A')})"],
            ["Writing", f"{scores.get('writing_score', 0)}%"],
            ["Formatting", f"{scores.get('formatting_score', 0)}%"],
            ["Structure", f"{scores.get('structure_score', 0)}%"],
        ]
        score_table = Table(score_data, colWidths=[3 * inch, 2 * inch])
        score_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
            ])
        )
        story.append(score_table)
        story.append(Spacer(1, 0.2 * inch))

        # Violations summary
        story.append(Paragraph(f"Violations ({len(violations)} total)", heading_style))
        if violations:
            viol_data = [["Type", "Category", "Severity", "Section"]]
            for v in violations[:30]:
                viol_data.append([
                    v.get("type", "")[:25],
                    v.get("category", "")[:12],
                    v.get("severity", "")[:8],
                    v.get("section", "")[:30],
                ])
            viol_table = Table(viol_data, colWidths=[1.5 * inch, 1 * inch, 0.8 * inch, 2.2 * inch])
            viol_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c5282")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ])
            )
            story.append(viol_table)
            if len(violations) > 30:
                story.append(Paragraph(f"... and {len(violations) - 30} more violations.", body_style))
        else:
            story.append(Paragraph("No violations detected.", body_style))

        # Recommendations
        story.append(Paragraph("Recommendations", heading_style))
        for rec in recommendations[:10]:
            text = rec.get("recommendation", "")
            sev = rec.get("severity", "info").upper()
            count = rec.get("count", 0)
            suffix = f" (×{count})" if count else ""
            story.append(Paragraph(f"<b>[{sev}]</b> {text}{suffix}", body_style))
            story.append(Spacer(1, 4))

        # Change log summary
        story.append(Paragraph(f"Changes Applied ({len(changes)} total)", heading_style))
        for change in changes[:15]:
            before = change.get("before", "")[:120]
            after = change.get("after", "")[:120]
            ctype = change.get("change_type", "")
            story.append(Paragraph(f"<b>{ctype}</b>: {before} → {after}", body_style))
            story.append(Spacer(1, 4))

        doc.build(story)
        logger.info(f"Compliance report saved: {self.output_path}")
        return str(self.output_path)
