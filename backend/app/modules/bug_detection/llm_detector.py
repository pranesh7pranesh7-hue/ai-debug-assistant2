"""LLM-based Bug Detector.
Uses the LLM to scan non-Python code for language-specific bugs, vulnerabilities, and logic errors.
"""
import json
import logging
from typing import Any, Dict, List

from app.modules.llm.llm_client import get_llm_client
from app.modules.llm.token_utils import truncate_context

logger = logging.getLogger("bugsense.llm_detector")


async def detect_bugs_with_llm(code: str, language: str) -> List[Dict[str, Any]]:
    """Scan code for bugs using LLM prompt tailored per language."""
    llm = get_llm_client()
    truncated_code = truncate_context(code, max_tokens=2500)

    prompt = (
        f"You are an expert {language} static analyzer and security auditor.\n"
        f"Analyze this {language} code for bugs, memory leaks, buffer overflows, undefined behavior, security vulnerabilities, syntax errors, and logic flaws.\n"
        f"Return ONLY a JSON array of bug objects. Do not include markdown formatting like ```json or any other text.\n"
        f"If no bugs are found, return an empty array [].\n\n"
        f"Each bug object must have the following fields:\n"
        f'- "line": integer line number where the issue occurs (approximate if needed)\n'
        f'- "column": integer column number (usually 0)\n'
        f'- "rule_id": string identifier for the rule (e.g., "LLM-MEM-001")\n'
        f'- "category": string, one of ["logic", "security", "resource_leak", "type_error", "syntax", "concurrency"]\n'
        f'- "message": string explaining the issue concisely\n\n'
        f"### Code to analyze:\n```\n{truncated_code}\n```"
    )

    system_instruction = f"You are a strict code analysis JSON API. Output only valid JSON."

    try:
        res = await llm.generate_json(prompt, system_instruction=system_instruction)
        
        findings: List[Dict[str, Any]] = []
        
        # In case the LLM returned a dict with a key instead of a list directly
        if isinstance(res, dict):
            # Sometimes LLM might wrap the array in a key like {"bugs": [...]}
            found_list = False
            for val in res.values():
                if isinstance(val, list):
                    res = val
                    found_list = True
                    break
            if not found_list:
                res = []
                
        if not isinstance(res, list):
            logger.warning("LLM bug detector did not return a list. Returned type: %s", type(res))
            return []

        for item in res:
            if isinstance(item, dict):
                findings.append({
                    "line": int(item.get("line", 1)),
                    "column": int(item.get("column", 0)),
                    "tool": "llm_detector",
                    "rule_id": str(item.get("rule_id", "LLM-GENERIC")),
                    "category": str(item.get("category", "logic")),
                    "message": str(item.get("message", "Detected potential issue.")),
                })
        return findings

    except Exception as e:
        logger.error("LLM bug detection failed: %s", str(e))
        return []
