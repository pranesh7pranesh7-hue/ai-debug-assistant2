"""TypeScript Language Analyzer.
Runs tsc (TypeScript Compiler) diagnostics when installed,
paired with static checks for 'any' type evasion, non-null assertion hazards, and type safety rules.
"""
import os
import re
import tempfile
from typing import Any, Dict, List, Optional
from app.analyzers.base import BaseAnalyzer, AnalysisResult, Issue


class TypeScriptAnalyzer(BaseAnalyzer):
    language: str = "TypeScript"

    async def analyze(
        self,
        code: str,
        filename: str = "app.ts",
        options: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        metrics = self.calculate_basic_metrics(code)
        issues: List[Issue] = []

        # 1. tsc Diagnostics if installed
        if self.is_tool_available("tsc"):
            with tempfile.TemporaryDirectory() as tmpdir:
                ts_file = os.path.join(tmpdir, "source.ts")
                with open(ts_file, "w", encoding="utf-8") as f:
                    f.write(code)

                cmd = ["tsc", "--noEmit", "--strict", ts_file]
                cmd_res = self.run_command(cmd, cwd=tmpdir, timeout=8)
                if cmd_res.stdout or cmd_res.stderr:
                    raw_out = (cmd_res.stdout + "\n" + cmd_res.stderr).strip()
                    parsed = self._parse_tsc_output(raw_out)
                    issues.extend(parsed)

        # 2. Deep TypeScript Static & Type-Safety Checks
        static_issues = self._run_static_ts_checks(code)
        issues.extend(static_issues)

        unique_issues = self._deduplicate_issues(issues)

        return AnalysisResult(
            language=self.language,
            filename=filename,
            status="completed",
            issues=unique_issues,
            complexity_metrics=metrics,
        )

    def _parse_tsc_output(self, output: str) -> List[Issue]:
        issues: List[Issue] = []
        # Pattern: source.ts(line,col): error TS2304: Cannot find name 'x'.
        pattern = re.compile(r"^([^(\n]+)\((\d+),(\d+)\):\s+(error|warning)\s+(TS\d+):\s+(.*)$", re.MULTILINE)
        for match in pattern.finditer(output):
            _, line_str, col_str, sev_str, code_str, msg = match.groups()
            line = int(line_str)
            col = int(col_str)
            severity = "Critical" if "error" in sev_str.lower() else "Medium"

            issues.append(
                Issue(
                    line=line,
                    column=col,
                    severity=severity,
                    type="Type Error",
                    code=code_str,
                    message=msg.strip(),
                    source="tsc",
                    suggestion="Fix TypeScript compiler type mismatch or missing definition.",
                )
            )
        return issues

    def _run_static_ts_checks(self, code: str) -> List[Issue]:
        issues: List[Issue] = []
        lines = code.splitlines()

        for idx, line in enumerate(lines, start=1):
            trimmed = line.strip()
            if trimmed.startswith("//") or trimmed.startswith("/*") or trimmed.startswith("*"):
                continue

            # Check 1: Explicit ': any' type disables TypeScript type safety
            if re.search(r':\s*any\b|\bas\s+any\b', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("any") + 1,
                        severity="Medium",
                        type="Type Safety Hazard",
                        code="TS-TYPE-ANY",
                        message="Use of 'any' type disables compile-time type verification.",
                        source="ts_static_analyzer",
                        suggestion="Replace 'any' with 'unknown', a generic type parameter, or an explicit interface.",
                    )
                )

            # Check 2: Non-null assertion operator '!' on potential undefined
            if re.search(r'[a-zA-Z_]\w*!\.[a-zA-Z_]', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("!.") + 1,
                        severity="High",
                        type="Null Safety Hazard",
                        code="TS-NULL-ASSERTION",
                        message="Non-null assertion operator ('!.') bypasses compiler null checks and can trigger runtime TypeError.",
                        source="ts_static_analyzer",
                        suggestion="Use optional chaining '?.' or an explicit null guard condition.",
                    )
                )

            # Check 3: Double type cast ('as unknown as T')
            if "as unknown as" in line or "as any as" in line:
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("as") + 1,
                        severity="High",
                        type="Unsafe Type Cast",
                        code="TS-UNSAFE-CAST",
                        message="Forced double type assertion ('as unknown as T') undermines type guarantees.",
                        source="ts_static_analyzer",
                        suggestion="Refactor types or write a type predicate (is) function to validate shape safely.",
                    )
                )

            # Check 4: eval usage
            if re.search(r'\beval\s*\(', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("eval") + 1,
                        severity="Critical",
                        type="Remote Code Execution",
                        code="TS-SEC-EVAL",
                        message="Dangerous 'eval()' usage detected in TypeScript code.",
                        source="ts_security_scanner",
                        suggestion="Avoid 'eval()'; use safe parsers or structured deserializers.",
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
