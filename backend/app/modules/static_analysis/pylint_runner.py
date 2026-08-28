"""Pylint Static Analysis Runner."""
import io
import json
import logging
import os
import tempfile
from typing import Any, Dict, List

logger = logging.getLogger("bugsense.pylint")


def run_pylint_analysis(code: str) -> List[Dict[str, Any]]:
    """Run Pylint on code string and normalize findings."""
    findings: List[Dict[str, Any]] = []

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
        tmp.write(code)
        tmp_path = tmp.name

    try:
        try:
            from pylint.lint import Run
            from pylint.reporters.text import TextReporter

            output = io.StringIO()
            reporter = TextReporter(output)
            # Run pylint with minimal noisy warnings disabled
            args = [
                tmp_path,
                "--output-format=json",
                "--disable=C0114,C0115,C0116,R0903",  # Disable missing docstrings & too few public methods
            ]
            
            # Using Pylint Run without exiting process and capturing output
            try:
                import contextlib
                from pylint.reporters import JSONReporter
                json_output = io.StringIO()
                with contextlib.redirect_stdout(json_output), contextlib.redirect_stderr(io.StringIO()):
                    Run(args[:1] + ["--output-format=json", "--disable=C0114,C0115,C0116,R0903"], reporter=JSONReporter(json_output), exit=False)
                raw_json = json_output.getvalue()
                if raw_json:
                    items = json.loads(raw_json)
                    for item in items:
                        msg_type = item.get("type", "warning")
                        category = "style"
                        if msg_type in ("error", "fatal"):
                            category = "logic"
                        elif msg_type == "warning":
                            category = "logic" if "un" in item.get("symbol", "") else "style"

                        findings.append({
                            "line": item.get("line", 1),
                            "column": item.get("column", 0),
                            "tool": "pylint",
                            "rule_id": item.get("symbol", f"PL-{item.get('message-id', '000')}"),
                            "message": item.get("message", "Pylint notice"),
                            "category": category,
                        })
            except Exception as pe:
                logger.debug("Pylint in-process run notice: %s", str(pe))

        except ImportError:
            logger.info("pylint not installed in environment, using internal linter rules.")

    except Exception as e:
        logger.warning("Pylint analysis exception: %s", str(e))
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    return findings
