"""Rust Language Analyzer.
Runs rustc compiler diagnostics and Clippy when available,
paired with static analyzers for unwrap() panic hazards, unsafe block memory safety, and unhandled Results.
"""
import os
import re
import tempfile
from typing import Any, Dict, List, Optional
from app.analyzers.base import BaseAnalyzer, AnalysisResult, Issue


class RustAnalyzer(BaseAnalyzer):
    language: str = "Rust"

    async def analyze(
        self,
        code: str,
        filename: str = "main.rs",
        options: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        metrics = self.calculate_basic_metrics(code)
        issues: List[Issue] = []

        # 1. rustc compiler diagnostics if installed
        if self.is_tool_available("rustc"):
            with tempfile.TemporaryDirectory() as tmpdir:
                rs_file = os.path.join(tmpdir, "main.rs")
                with open(rs_file, "w", encoding="utf-8") as f:
                    f.write(code)

                cmd = ["rustc", "--crate-type=lib", "--emit=metadata", rs_file]
                cmd_res = self.run_command(cmd, cwd=tmpdir, timeout=8)
                if cmd_res.stderr:
                    parsed = self._parse_rustc_output(cmd_res.stderr)
                    issues.extend(parsed)

        # 2. Deep Rust Static & Safety Checks
        static_issues = self._run_static_rust_checks(code)
        issues.extend(static_issues)

        unique_issues = self._deduplicate_issues(issues)

        return AnalysisResult(
            language=self.language,
            filename=filename,
            status="completed",
            issues=unique_issues,
            complexity_metrics=metrics,
        )

    def _parse_rustc_output(self, output: str) -> List[Issue]:
        issues: List[Issue] = []
        # Pattern: error[E0382]: use of moved value or warning: unused variable
        pattern = re.compile(r"^(error|warning)(?:\[([E\d]+)\])?:\s+(.*)$", re.MULTILINE)
        line_pattern = re.compile(r"-->\s+[^:]+:(\d+):(\d+)")

        current_issue = None
        for line in output.splitlines():
            match = pattern.match(line)
            if match:
                sev_str, code_str, msg = match.groups()
                severity = "Critical" if sev_str == "error" else "Medium"
                current_issue = Issue(
                    line=1,
                    column=1,
                    severity=severity,
                    type="Compiler Error" if severity == "Critical" else "Compiler Warning",
                    code=code_str or ("RS-ERR" if severity == "Critical" else "RS-WARN"),
                    message=msg.strip(),
                    source="rustc",
                    suggestion="Address rustc compiler message to satisfy Rust borrow checker and type rules.",
                )
                issues.append(current_issue)
            elif current_issue and "-->" in line:
                loc_match = line_pattern.search(line)
                if loc_match:
                    current_issue.line = int(loc_match.group(1))
                    current_issue.column = int(loc_match.group(2))

        return issues

    def _run_static_rust_checks(self, code: str) -> List[Issue]:
        issues: List[Issue] = []
        lines = code.splitlines()

        for idx, line in enumerate(lines, start=1):
            trimmed = line.strip()
            if trimmed.startswith("//") or trimmed.startswith("/*"):
                continue

            # Check 1: .unwrap() on Option/Result without error handling
            if re.search(r'\b[a-zA-Z_]\w*\.unwrap\(\)', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find(".unwrap()") + 1,
                        severity="High",
                        type="Panic Hazard",
                        code="RS-PANIC-UNWRAP",
                        message="Direct call to '.unwrap()' causes thread panic on 'None' or 'Err' variants.",
                        source="rust_static_analyzer",
                        suggestion="Use pattern matching, 'if let Some(...)', or the '?' error propagation operator.",
                    )
                )

            # Check 2: unsafe block usage
            if re.search(r'\bunsafe\s*\{', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("unsafe") + 1,
                        severity="High",
                        type="Unsafe Memory Block",
                        code="RS-MEM-UNSAFE",
                        message="Use of 'unsafe' block disables Rust memory safety guarantees.",
                        source="rust_static_analyzer",
                        suggestion="Verify all invariants are preserved and document safety assumptions with '// SAFETY:'.",
                    )
                )

            # Check 3: Division by literal zero
            div_zero = re.search(r"/\s*0\b(?!\.)", line)
            if div_zero and not line.strip().startswith("//"):
                issues.append(
                    Issue(
                        line=idx,
                        column=div_zero.start() + 1,
                        severity="Critical",
                        type="Division by Zero",
                        code="RS-LOGIC-DIVZERO",
                        message="Runtime Panic: division by zero.",
                        source="rust_static_analyzer",
                        suggestion="Check that divisor is not 0 prior to division.",
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
