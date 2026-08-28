"""Shell / Bash Language Analyzer.
Runs ShellCheck when installed,
paired with static analyzers for unquoted variables ($VAR), missing error traps (set -e), dangerous eval, and wildcard deletion hazards.
"""
import json
import os
import re
import tempfile
from typing import Any, Dict, List, Optional
from app.analyzers.base import BaseAnalyzer, AnalysisResult, Issue


class ShellAnalyzer(BaseAnalyzer):
    language: str = "Shell"

    async def analyze(
        self,
        code: str,
        filename: str = "script.sh",
        options: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        metrics = self.calculate_basic_metrics(code)
        issues: List[Issue] = []

        # 1. ShellCheck if available
        if self.is_tool_available("shellcheck"):
            with tempfile.TemporaryDirectory() as tmpdir:
                sh_file = os.path.join(tmpdir, "script.sh")
                with open(sh_file, "w", encoding="utf-8") as f:
                    f.write(code)

                cmd = ["shellcheck", "-f", "json", sh_file]
                cmd_res = self.run_command(cmd, cwd=tmpdir, timeout=8)
                if cmd_res.stdout:
                    parsed = self._parse_shellcheck_json(cmd_res.stdout)
                    issues.extend(parsed)

        # 2. Deep Shell Static Checks
        static_issues = self._run_static_shell_checks(code)
        issues.extend(static_issues)

        unique_issues = self._deduplicate_issues(issues)

        return AnalysisResult(
            language=self.language,
            filename=filename,
            status="completed",
            issues=unique_issues,
            complexity_metrics=metrics,
        )

    def _parse_shellcheck_json(self, output: str) -> List[Issue]:
        issues: List[Issue] = []
        try:
            items = json.loads(output)
            for it in items:
                sev_map = {"error": "Critical", "warning": "High", "info": "Medium", "style": "Low"}
                sev = sev_map.get(it.get("level", "warning"), "Medium")
                issues.append(
                    Issue(
                        line=it.get("line", 1),
                        column=it.get("column", 1),
                        severity=sev,
                        type="ShellCheck Finding",
                        code=f"SC{it.get('code', 0)}",
                        message=it.get("message", "Shell issue"),
                        source="shellcheck",
                        suggestion="Follow ShellCheck remediation recommendations.",
                    )
                )
        except Exception:
            pass
        return issues

    def _run_static_shell_checks(self, code: str) -> List[Issue]:
        issues: List[Issue] = []
        lines = code.splitlines()

        # Check 1: Missing 'set -e' or 'set -o errexit' in non-trivial scripts
        if len(lines) > 5 and not any("set -e" in l or "set -o errexit" in l or "set -euo pipefail" in l for l in lines[:10]):
            issues.append(
                Issue(
                    line=1,
                    column=1,
                    severity="Medium",
                    type="Reliability Practice",
                    code="SH-MISSING-ERREXIT",
                    message="Bash script missing 'set -e' / 'set -euo pipefail'. Script will continue executing following command failures.",
                    source="shell_static_analyzer",
                    suggestion="Add 'set -euo pipefail' near top of script to halt execution immediately upon unhandled error.",
                )
            )

        for idx, line in enumerate(lines, start=1):
            trimmed = line.strip()
            if trimmed.startswith("#"):
                continue

            # Check 2: Unquoted variable in destructive command (rm -rf $DIR)
            if re.search(r'\brm\s+(-[rfRF]+\s+)?\$[a-zA-Z_]\w*', line) and '"$' not in line:
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("$") + 1,
                        severity="Critical",
                        type="Destructive Command Hazard",
                        code="SH-UNQUOTED-RM-VAR",
                        message="Unquoted variable in 'rm' command. If variable is unset or contains spaces, this may delete root '/' or unintended directories.",
                        source="shell_security_scanner",
                        suggestion='Always double-quote variables in file operations: \'rm -rf "${DIR:?}"\'.',
                    )
                )

            # Check 3: eval with dynamic variables
            if re.search(r'\beval\s+.*\$', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("eval") + 1,
                        severity="Critical",
                        type="Command Injection",
                        code="SH-DANGEROUS-EVAL",
                        message="Use of 'eval' with dynamic variables creates shell command injection hazards.",
                        source="shell_security_scanner",
                        suggestion="Refactor using arrays or native bash parameter expansion instead of 'eval'.",
                    )
                )

            # Check 4: Unchecked cd command followed by operations (cd $DIR; rm -rf *)
            if re.search(r'\bcd\s+[^&|;]+;\s*rm\b', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=1,
                        severity="High",
                        type="Directory Traversal Hazard",
                        code="SH-UNCHECKED-CD",
                        message="Unchecked 'cd' before 'rm'. If 'cd' fails, 'rm' executes in the current working directory.",
                        source="shell_static_analyzer",
                        suggestion="Check cd exit code: 'cd \"$DIR\" && rm -rf *' or 'cd \"$DIR\" || exit 1'.",
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
