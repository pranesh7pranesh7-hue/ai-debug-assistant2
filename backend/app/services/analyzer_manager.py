"""Analyzer Manager Service.
Dispatches analysis for single files or multi-file projects across all supported languages,
grouping and combining results.
"""
from typing import Any, Dict, List, Optional
from app.analyzers import get_analyzer
from app.analyzers.base import AnalysisResult
from app.services.language_detector import LanguageDetector


class AnalyzerManager:
    """Coordinates multi-language analysis execution across single and multi-file submissions."""

    @classmethod
    async def analyze_code(
        cls,
        code: str,
        filename: str = "code.py",
        language: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        """Analyze a single code string with automatic or explicit language dispatch."""
        detected_lang = language or LanguageDetector.detect_language(filename=filename, code=code)
        analyzer = get_analyzer(detected_lang)
        return await analyzer.analyze(code=code, filename=filename, options=options)

    @classmethod
    async def analyze_project_files(
        cls,
        files: List[Dict[str, str]],  # List of {"path": rel_path, "code": code_str}
        project_name: str = "Project",
    ) -> Dict[str, Any]:
        """Analyze multiple project files across different languages and aggregate findings."""
        all_issues: List[Dict[str, Any]] = []
        file_results: List[Dict[str, Any]] = []
        languages_detected: set = set()
        total_loc = 0

        severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
        language_issue_counts: Dict[str, int] = {}

        for item in files:
            rel_path = item.get("path", "file.py")
            code_str = item.get("code", "")
            total_loc += len(code_str.splitlines())

            lang = LanguageDetector.detect_language(filename=rel_path, code=code_str)
            languages_detected.add(lang)

            analyzer = get_analyzer(lang)
            res = await analyzer.analyze(code=code_str, filename=rel_path)

            file_issues = []
            for iss in res.issues:
                iss_dict = iss.to_dict()
                iss_dict["file_path"] = rel_path
                iss_dict["language"] = lang
                all_issues.append(iss_dict)
                file_issues.append(iss_dict)

                severity_counts[iss.severity] = severity_counts.get(iss.severity, 0) + 1
                language_issue_counts[lang] = language_issue_counts.get(lang, 0) + 1

            file_results.append({
                "file_path": rel_path,
                "language": lang,
                "issues_count": len(res.issues),
                "issues": file_issues,
                "complexity_metrics": res.complexity_metrics,
            })

        return {
            "project_name": project_name,
            "total_files": len(files),
            "total_lines_of_code": total_loc,
            "languages_detected": sorted(list(languages_detected)),
            "total_issues": len(all_issues),
            "severity_breakdown": severity_counts,
            "language_breakdown": language_issue_counts,
            "files": file_results,
            "all_issues": all_issues,
        }
