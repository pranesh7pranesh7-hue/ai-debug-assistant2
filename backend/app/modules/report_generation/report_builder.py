"""Report Generation Module.
Builds structured reports per analysis run with statistics, severity distributions, diffs, and PDF paths.
"""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List
from sqlalchemy.orm import Session

from app.models.bug import Bug
from app.models.code_submission import CodeSubmission
from app.models.fix import Fix
from app.models.report import Report
from app.modules.report_generation.pdf_exporter import PDFExporter


class ReportBuilder:
    """Builds and persists structured audit reports for code submissions."""

    @staticmethod
    def generate_report(db: Session, submission_id: int) -> Report:
        """Construct full JSON summary, render HTML/PDF, and save to reports table."""
        sub = db.query(CodeSubmission).filter(CodeSubmission.id == submission_id).first()
        if not sub:
            raise ValueError(f"Submission {submission_id} not found.")

        bugs = db.query(Bug).filter(Bug.submission_id == submission_id).all()
        fixes = (
            db.query(Fix)
            .join(Bug)
            .filter(Bug.submission_id == submission_id, Fix.status == "verified")
            .all()
        )

        severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
        category_counts: Dict[str, int] = {}

        bug_list_data: List[Dict[str, Any]] = []
        for b in bugs:
            severity_counts[b.severity] = severity_counts.get(b.severity, 0) + 1
            category_counts[b.category] = category_counts.get(b.category, 0) + 1
            bug_list_data.append({
                "id": b.id,
                "line": b.line,
                "column": b.column,
                "tool": b.tool,
                "rule_id": b.rule_id,
                "category": b.category,
                "message": b.message,
                "severity": b.severity,
                "severity_score": b.severity_score,
                "explanation": b.explanation,
            })

        verified_fixes_data: List[Dict[str, Any]] = []
        for f in fixes:
            verified_fixes_data.append({
                "bug_id": f.bug_id,
                "line": f.bug.line,
                "rule_id": f.bug.rule_id,
                "rationale": f.rationale,
                "diff_text": f.diff_text,
            })

        report_dict: Dict[str, Any] = {
            "submission_id": sub.id,
            "filename": sub.filename,
            "source_hash": sub.source_hash,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "total_bugs": len(bugs),
            "critical_count": severity_counts.get("Critical", 0),
            "high_count": severity_counts.get("High", 0),
            "medium_count": severity_counts.get("Medium", 0),
            "low_count": severity_counts.get("Low", 0),
            "info_count": severity_counts.get("Info", 0),
            "auto_fixed_count": len(fixes),
            "complexity_score": 2.5,
            "severity_breakdown": severity_counts,
            "category_breakdown": category_counts,
            "bugs": bug_list_data,
            "verified_fixes": verified_fixes_data,
        }

        # Render HTML and export PDF
        html_rendered = PDFExporter.render_html_report(report_dict)
        report_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "storage", "reports")
        os.makedirs(report_dir, exist_ok=True)
        pdf_file_path = os.path.join(report_dir, f"report_sub_{submission_id}.pdf")

        PDFExporter.export_pdf_file(html_rendered, pdf_file_path)

        # Check existing report
        db_report = db.query(Report).filter(Report.submission_id == submission_id).first()
        if not db_report:
            db_report = Report(
                submission_id=submission_id,
                summary_json=json.dumps(report_dict),
                pdf_path=pdf_file_path,
            )
            db.add(db_report)
        else:
            db_report.summary_json = json.dumps(report_dict)
            db_report.pdf_path = pdf_file_path

        db.commit()
        db.refresh(db_report)
        return db_report
