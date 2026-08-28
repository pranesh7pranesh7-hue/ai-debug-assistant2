"""Ruby Language Analyzer.
Runs 'ruby -c' syntax verification when installed,
paired with static analyzers for ActiveRecord SQL injection, Command Injection (backticks/system), and Marshal deserialization.
"""
import os
import re
import tempfile
from typing import Any, Dict, List, Optional
from app.analyzers.base import BaseAnalyzer, AnalysisResult, Issue


class RubyAnalyzer(BaseAnalyzer):
    language: str = "Ruby"

    async def analyze(
        self,
        code: str,
        filename: str = "app.rb",
        options: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        metrics = self.calculate_basic_metrics(code)
        issues: List[Issue] = []

        # 1. Ruby -c syntax check if installed
        if self.is_tool_available("ruby"):
            with tempfile.TemporaryDirectory() as tmpdir:
                rb_file = os.path.join(tmpdir, "source.rb")
                with open(rb_file, "w", encoding="utf-8") as f:
                    f.write(code)

                cmd = ["ruby", "-c", rb_file]
                cmd_res = self.run_command(cmd, cwd=tmpdir, timeout=6)
                if not cmd_res.success or "Syntax OK" not in cmd_res.stdout:
                    raw = cmd_res.stdout + "\n" + cmd_res.stderr
                    parsed = self._parse_ruby_syntax_output(raw)
                    if parsed:
                        issues.append(parsed)

        # 2. Deep Ruby Static Checks
        static_issues = self._run_static_ruby_checks(code)
        issues.extend(static_issues)

        unique_issues = self._deduplicate_issues(issues)

        return AnalysisResult(
            language=self.language,
            filename=filename,
            status="completed",
            issues=unique_issues,
            complexity_metrics=metrics,
        )

    def _parse_ruby_syntax_output(self, output: str) -> Optional[Issue]:
        match = re.search(r"source\.rb:(\d+):\s*(syntax error.*?)(?:\n|$)", output, re.IGNORECASE)
        if match:
            line_str, msg = match.groups()
            return Issue(
                line=int(line_str),
                column=1,
                severity="Critical",
                type="Ruby Syntax Error",
                code="RB-SYNTAX-ERR",
                message=msg.strip(),
                source="ruby_syntax_checker",
                suggestion="Fix Ruby syntax on the flagged line.",
            )
        return None

    def _run_static_ruby_checks(self, code: str) -> List[Issue]:
        issues: List[Issue] = []
        lines = code.splitlines()

        for idx, line in enumerate(lines, start=1):
            trimmed = line.strip()
            if trimmed.startswith("#"):
                continue

            # Check 1: ActiveRecord SQL Injection via string interpolation
            if re.search(r'\.(where|find_by|order|having)\s*\(\s*["\'].*#\{', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=1,
                        severity="Critical",
                        type="SQL Injection",
                        code="RB-SEC-SQLI",
                        message="ActiveRecord SQL Injection: query string constructed using #{...} interpolation.",
                        source="ruby_security_scanner",
                        suggestion="Use parameterized query hash or placeholders: 'where(\"name = ?\", param)' or 'where(name: param)'.",
                    )
                )

            # Check 2: Command Injection via backticks or system()
            if (re.search(r'`.*#\{.*`', line) or re.search(r'\b(system|exec|%x)\s*\(?.*#\{', line)) and not line.strip().startswith("#"):
                issues.append(
                    Issue(
                        line=idx,
                        column=1,
                        severity="Critical",
                        type="Command Injection",
                        code="RB-SEC-CMD-INJ",
                        message="Command Injection vulnerability: executing shell command containing unescaped string interpolation.",
                        source="ruby_security_scanner",
                        suggestion="Avoid shell execution or pass arguments as a safe array: 'system(\"cmd\", arg1, arg2)'.",
                    )
                )

            # Check 3: Insecure Deserialization via Marshal.load
            if re.search(r'\bMarshal\.load\s*\(', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("Marshal.load") + 1,
                        severity="Critical",
                        type="Insecure Deserialization",
                        code="RB-SEC-MARSHAL",
                        message="Insecure Deserialization: 'Marshal.load' on untrusted input allows Remote Code Execution.",
                        source="ruby_security_scanner",
                        suggestion="Use 'JSON.parse' for serialization of external data.",
                    )
                )

            # Check 4: Bare rescue capturing Exception instead of StandardError
            if re.search(r'\brescue\s+Exception\b', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("Exception") + 1,
                        severity="High",
                        type="Error Handling Bug",
                        code="RB-ERR-RESCUE-EXCEPTION",
                        message="Rescuing 'Exception' intercepts system exit, interrupts (Ctrl+C), and fatal VM signals.",
                        source="ruby_static_analyzer",
                        suggestion="Rescue 'StandardError' or specific exception subclasses instead of 'Exception'.",
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
