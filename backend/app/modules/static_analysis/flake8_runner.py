"""Flake8 Static Analysis Runner."""
import logging
import os
import re
import subprocess
import sys
import tempfile
from typing import Any, Dict, List

logger = logging.getLogger("bugsense.flake8")


def run_flake8_analysis(code: str) -> List[Dict[str, Any]]:
    """Run Flake8 on code string and normalize findings."""
    findings: List[Dict[str, Any]] = []

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        # Run flake8 as subprocess
        result = subprocess.run(
            [sys.executable, "-m", "flake8", "--isolated", "--max-line-length=120", tmp_path],
            capture_output=True,
            text=True,
            timeout=5,
        )

        output = result.stdout + result.stderr
        for line in output.splitlines():
            # Format: filename:line:col: CODE message
            match = re.match(r"^.+?:(\d+):(\d+):\s*([A-Z]\d+)\s*(.+)$", line.strip())
            if match:
                lineno = int(match.group(1))
                col = int(match.group(2))
                code_id = match.group(3)
                msg = match.group(4)

                category = "style"
                if code_id.startswith("F"):  # Pyflakes (undefined vars, unused imports, etc.)
                    category = "logic"
                elif code_id.startswith("E9") or code_id.startswith("F7"):  # Syntax
                    category = "syntax"

                findings.append({
                    "line": lineno,
                    "column": col,
                    "tool": "flake8",
                    "rule_id": code_id,
                    "message": msg,
                    "category": category,
                })

    except Exception as e:
        logger.debug("Flake8 run note: %s", str(e))
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    return findings
