"""Python Language Analyzer.
Runs Pylint, Flake8, Bandit, Radon complexity metrics, and AST semantic detectors.
"""
from typing import Any, Dict, List, Optional
from app.analyzers.base import BaseAnalyzer, AnalysisResult, Issue
from app.modules.bug_detection.detector import detect_all_bugs
from app.modules.code_upload.validators import validate_python_code
from app.core.exceptions import CodeSyntaxError, ValidationError


class PythonAnalyzer(BaseAnalyzer):
    language: str = "Python"

    async def analyze(
        self,
        code: str,
        filename: str = "code.py",
        options: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        metrics = self.calculate_basic_metrics(code)
        issues: List[Issue] = []

        # 1. Pre-validate syntax via AST
        try:
            validate_python_code(code, filename=filename)
        except CodeSyntaxError as e:
            issues.append(
                Issue(
                    line=e.details.get("line", 1),
                    column=e.details.get("column", 0),
                    severity="Critical",
                    type="Syntax Error",
                    code="PY-SYNTAX-001",
                    message=e.message,
                    source="python_ast",
                    suggestion="Review Python syntax on the flagged line and correct colons, indentation, or unclosed brackets.",
                )
            )
            return AnalysisResult(
                language=self.language,
                filename=filename,
                status="syntax_error",
                issues=issues,
                complexity_metrics=metrics,
                summary_message="Python syntax error prevented full static analysis.",
            )
        except ValidationError as e:
            return AnalysisResult(
                language=self.language,
                filename=filename,
                status="completed",
                issues=[],
                complexity_metrics=metrics,
                summary_message=e.message,
            )

        # 2. Run static analyzers + deep pattern detectors
        try:
            findings, detailed_metrics = await detect_all_bugs(code)
            if detailed_metrics:
                metrics.update(detailed_metrics)

            for f in findings:
                sev = f.get("category", "").lower()
                severity = "Medium"
                if "security" in sev or "critical" in sev:
                    severity = "Critical"
                elif "logic" in sev or "error" in sev or "bug" in sev:
                    severity = "High"
                elif "style" in sev or "convention" in sev:
                    severity = "Low"

                issues.append(
                    Issue(
                        line=f.get("line", 1),
                        column=f.get("column", 0),
                        severity=f.get("severity", severity),
                        type=f.get("category", "Logic").capitalize(),
                        code=f.get("rule_id", "PY-001"),
                        message=f.get("message", "Python defect detected"),
                        source=f.get("tool", "pylint"),
                        suggestion=f.get("suggestion", "Refactor the flagged line to comply with Python best practices."),
                    )
                )

            return AnalysisResult(
                language=self.language,
                filename=filename,
                status="completed",
                issues=issues,
                complexity_metrics=metrics,
            )
        except Exception as ex:
            return AnalysisResult(
                language=self.language,
                filename=filename,
                status="completed",
                issues=issues,
                complexity_metrics=metrics,
                summary_message=f"Analysis completed with notice: {str(ex)}",
            )
