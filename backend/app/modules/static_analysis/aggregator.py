"""Static Analysis Aggregator.
Runs all static analyzers in parallel and unifies findings into standard schema:
{
    "line": int,
    "column": int,
    "tool": str,
    "rule_id": str,
    "message": str,
    "category": str
}
"""
import asyncio
from typing import Any, Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor

from app.modules.static_analysis.ast_parser import run_ast_analysis
from app.modules.static_analysis.pylint_runner import run_pylint_analysis
from app.modules.static_analysis.flake8_runner import run_flake8_analysis
from app.modules.static_analysis.bandit_runner import run_bandit_analysis
from app.modules.static_analysis.complexity_analyzer import analyze_complexity


async def run_all_static_analyzers(code: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Run AST, Pylint, Flake8, Bandit, and Radon analyzers concurrently."""
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=5) as executor:
        ast_task = loop.run_in_executor(executor, run_ast_analysis, code)
        pylint_task = loop.run_in_executor(executor, run_pylint_analysis, code)
        flake8_task = loop.run_in_executor(executor, run_flake8_analysis, code)
        bandit_task = loop.run_in_executor(executor, run_bandit_analysis, code)
        complexity_task = loop.run_in_executor(executor, analyze_complexity, code)

        results = await asyncio.gather(
            ast_task,
            pylint_task,
            flake8_task,
            bandit_task,
            complexity_task,
            return_exceptions=True,
        )
        ast_res, pylint_res, flake8_res, bandit_res, comp_raw = results
        complexity_res = []
        metrics = None
        if isinstance(comp_raw, tuple) and len(comp_raw) == 2:
            complexity_res, metrics = comp_raw

    all_findings: List[Dict[str, Any]] = []

    for res in (ast_res, pylint_res, flake8_res, bandit_res, complexity_res):
        if isinstance(res, list):
            for item in res:
                if isinstance(item, dict) and "line" in item:
                    all_findings.append({
                        "line": int(item.get("line", 1)),
                        "column": int(item.get("column", 0)),
                        "tool": str(item.get("tool", "unknown")),
                        "rule_id": str(item.get("rule_id", "GENERIC")),
                        "message": str(item.get("message", "")),
                        "category": str(item.get("category", "logic")),
                    })

    calc_metrics = metrics if isinstance(metrics, dict) else {
        "average_complexity": 1.0,
        "maintainability_index": 85.0,
        "total_functions": 0,
    }

    return all_findings, calc_metrics
