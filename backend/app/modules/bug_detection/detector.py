import logging
from typing import Any, Dict, List, Tuple

from app.modules.bug_detection.deduper import deduplicate_bugs
from app.modules.bug_detection.patterns import find_pattern_bugs
from app.modules.static_analysis.aggregator import run_all_static_analyzers

logger = logging.getLogger("bugsense.detector")


async def detect_all_bugs(code: str, language: str = "Python") -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Execute complete bug detection pipeline:
    1. Language-specific static analyzers from AnalyzerManager (Java, JS, C++, Go, Rust, C#, PHP, Swift, Ruby, SQL, etc.)
    2. Deep AST semantic bug pattern detectors (for Python)
    3. Multi-language LLM-based bug detector (tailored for the specific language rules)
    4. Aggregation and multi-tool deduplication
    """
    combined: List[Dict[str, Any]] = []
    complexity_metrics: Dict[str, Any] = {
        "average_complexity": 1.0,
        "maintainability_index": 85.0,
        "total_functions": 0,
    }

    # 1. For Python: run Python-specific static analyzers (AST, Flake8, Bandit, Radon, Pylint) + AST pattern detectors
    if language == "Python":
        try:
            static_findings, py_metrics = await run_all_static_analyzers(code)
            if py_metrics:
                complexity_metrics.update(py_metrics)
            pattern_findings = find_pattern_bugs(code)
            combined.extend(static_findings)
            combined.extend(pattern_findings)
        except Exception as e:
            logger.warning(f"Python static analysis warning: {e}")
    else:
        # 2. For non-Python: run language-specific static analyzer (C, C++, Java, JS, TS, Go, Rust, C#, PHP, etc.)
        from app.analyzers import get_analyzer
        analyzer = get_analyzer(language)
        try:
            analysis_res = await analyzer.analyze(code=code, filename=f"code.{language.lower()}")
            if analysis_res.complexity_metrics:
                complexity_metrics.update(analysis_res.complexity_metrics)

            for iss in analysis_res.issues:
                combined.append({
                    "line": iss.line,
                    "column": iss.column,
                    "tool": iss.source or f"{language.lower()}_analyzer",
                    "rule_id": iss.code or f"{language.upper()}-STATIC",
                    "category": iss.type.lower() if iss.type else "logic",
                    "message": iss.message,
                })
        except Exception as e:
            logger.warning(f"Static analyzer failed for {language}: {e}")

        # 3. For non-Python: also run LLM-based detector for deeper language-specific rules
        try:
            from app.modules.bug_detection.llm_detector import detect_bugs_with_llm
            llm_findings = await detect_bugs_with_llm(code, language)
            combined.extend(llm_findings)
        except Exception as e:
            logger.warning(f"LLM bug detection warning for {language}: {e}")

    # 4. Deduplicate across static analyzers and LLM detectors
    deduped = deduplicate_bugs(combined)

    return deduped, complexity_metrics
