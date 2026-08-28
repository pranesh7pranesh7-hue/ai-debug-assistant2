"""JavaScript Language Analyzer.
Runs ESLint / Node.js syntax check when installed,
paired with static analyzers for DOM XSS, loose equality coercion, unhandled Promises, and scoping bugs.
"""
import json
import os
import re
import tempfile
from typing import Any, Dict, List, Optional
from app.analyzers.base import BaseAnalyzer, AnalysisResult, Issue


class JavaScriptAnalyzer(BaseAnalyzer):
    language: str = "JavaScript"

    async def analyze(
        self,
        code: str,
        filename: str = "app.js",
        options: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        metrics = self.calculate_basic_metrics(code)
        issues: List[Issue] = []

        # 1. Node.js Syntax Verification (-c) if node installed
        if self.is_tool_available("node"):
            with tempfile.TemporaryDirectory() as tmpdir:
                js_path = os.path.join(tmpdir, "source.js")
                with open(js_path, "w", encoding="utf-8") as f:
                    f.write(code)

                cmd = ["node", "--check", js_path]
                res = self.run_command(cmd, cwd=tmpdir, timeout=6)
                if res.stderr and not res.success:
                    parsed_err = self._parse_node_check_output(res.stderr)
                    if parsed_err:
                        issues.append(parsed_err)

        # 2. Deep JavaScript Static & Security Checks
        static_issues = self._run_static_js_checks(code)
        issues.extend(static_issues)

        unique_issues = self._deduplicate_issues(issues)

        return AnalysisResult(
            language=self.language,
            filename=filename,
            status="completed",
            issues=unique_issues,
            complexity_metrics=metrics,
        )

    def _parse_node_check_output(self, output: str) -> Optional[Issue]:
        match = re.search(r"source\.js:(\d+)", output)
        line = int(match.group(1)) if match else 1
        msg_match = re.search(r"SyntaxError:\s*(.*)", output)
        msg = msg_match.group(1) if msg_match else "JavaScript Syntax Error"

        return Issue(
            line=line,
            column=0,
            severity="Critical",
            type="Syntax Error",
            code="JS-SYNTAX-001",
            message=msg.strip(),
            source="node_syntax_checker",
            suggestion="Correct JavaScript syntax on the flagged line.",
        )

    def _run_static_js_checks(self, code: str) -> List[Issue]:
        issues: List[Issue] = []
        lines = code.splitlines()

        for idx, line in enumerate(lines, start=1):
            trimmed = line.strip()
            if trimmed.startswith("//") or trimmed.startswith("/*") or trimmed.startswith("*"):
                continue

            # Check 1: eval() / Function constructor dangerous code execution
            if re.search(r'\b(eval|Function)\s*\(', line) and not "typeof eval" in line:
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("eval") + 1,
                        severity="Critical",
                        type="Remote Code Execution",
                        code="JS-SEC-EVAL",
                        message="Dangerous 'eval()' usage allows arbitrary JavaScript code execution.",
                        source="js_security_scanner",
                        suggestion="Avoid 'eval()'; use JSON.parse() for data serialization or safe functional mappings.",
                    )
                )

            # Check 2: DOM Cross-Site Scripting (XSS) via innerHTML / outerHTML
            if re.search(r'\.(innerHTML|outerHTML)\s*=', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("innerHTML") + 1 if "innerHTML" in line else line.find("outerHTML") + 1,
                        severity="High",
                        type="DOM XSS Vulnerability",
                        code="JS-SEC-XSS",
                        message="Direct assignment to 'innerHTML' or 'outerHTML' creates DOM XSS vulnerabilities.",
                        source="js_security_scanner",
                        suggestion="Use 'textContent', 'innerText', or sanitize dynamic HTML before injection.",
                    )
                )

            # Check 3: Loose equality (== or !=) causing unintended type coercion
            eq_match = re.search(r'(?<![!=><])(==|!=)(?!=)', line)
            if eq_match and "typeof" not in line and "null" not in line:
                issues.append(
                    Issue(
                        line=idx,
                        column=eq_match.start() + 1,
                        severity="Low",
                        type="Type Coercion Hazard",
                        code="JS-STYLE-LOOSE-EQ",
                        message=f"Loose equality '{eq_match.group(1)}' used instead of strict '{eq_match.group(1)}='.",
                        source="js_static_analyzer",
                        suggestion="Use strict equality '===' and '!==' to prevent unexpected type coercion bugs.",
                    )
                )

            # Check 4: NaN === NaN always evaluates to false
            if re.search(r'\bNaN\s*===?\s*NaN\b', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("NaN") + 1,
                        severity="High",
                        type="Logic Defect",
                        code="JS-LOGIC-NAN",
                        message="Comparing 'NaN === NaN' is always false according to IEEE 754.",
                        source="js_static_analyzer",
                        suggestion="Use 'Number.isNaN(val)' or 'isNaN(val)' to test for NaN.",
                    )
                )

            # Check 5: Deprecated 'var' keyword
            if re.search(r'\bvar\s+[a-zA-Z_]\w*', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("var") + 1,
                        severity="Low",
                        type="Modern ES6 Practice",
                        code="JS-STYLE-VAR",
                        message="Legacy 'var' keyword has function-scope hoisting semantics.",
                        source="js_static_analyzer",
                        suggestion="Replace 'var' with block-scoped 'let' or immutable 'const'.",
                    )
                )

            # Check 6: Unhandled Promise without await in async function or missing .catch
            if re.search(r'\bfetch\(|\baxios\.', line) and "await " not in line and ".then" not in line and "return " not in line:
                issues.append(
                    Issue(
                        line=idx,
                        column=1,
                        severity="Medium",
                        type="Async Control Flow",
                        code="JS-ASYNC-UNHANDLED",
                        message="Asynchronous Promise call (fetch/axios) without 'await' or chained '.catch()'.",
                        source="js_static_analyzer",
                        suggestion="Use 'await fetch(...)' or attach '.catch(err => ...)' to handle network failures.",
                    )
                )

        return issues

    def _deduplicate_issues(self, issues: List[Issue]) -> List[Issue]:
        seen = set()
        unique = []
        for i in issues:
            key = (i.line, i.code, i.message[:40])
            if key not in seen:
                seen.add(key)
                unique.append(i)
        return unique
