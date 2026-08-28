"""Bandit Security Vulnerability Scanner Runner."""
import json
import logging
import os
import subprocess
import sys
import tempfile
from typing import Any, Dict, List

logger = logging.getLogger("bugsense.bandit")


def run_bandit_analysis(code: str) -> List[Dict[str, Any]]:
    """Run Bandit security scanner on code string and normalize findings."""
    findings: List[Dict[str, Any]] = []

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [sys.executable, "-m", "bandit", "-f", "json", "-q", tmp_path],
            capture_output=True,
            text=True,
            timeout=5,
        )

        output_str = result.stdout.strip()
        if output_str:
            try:
                data = json.loads(output_str)
                results = data.get("results", [])
                for item in results:
                    findings.append({
                        "line": item.get("line_number", 1),
                        "column": item.get("col_offset", 0),
                        "tool": "bandit",
                        "rule_id": item.get("test_id", "B000"),
                        "message": f"[{item.get('issue_severity', 'MEDIUM')} Security] {item.get('issue_text', 'Potential security vulnerability')}",
                        "category": "security",
                    })
            except json.JSONDecodeError:
                pass

    except Exception as e:
        logger.debug("Bandit run note: %s", str(e))
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    return findings
