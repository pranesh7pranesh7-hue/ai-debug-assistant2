"""Swift Language Analyzer.
Runs swiftc compiler diagnostics when installed,
paired with static checks for forced optional unwrapping (!), closure retain cycles ([weak self]), and forced try! crashes.
"""
import os
import re
import tempfile
from typing import Any, Dict, List, Optional
from app.analyzers.base import BaseAnalyzer, AnalysisResult, Issue


class SwiftAnalyzer(BaseAnalyzer):
    language: str = "Swift"

    async def analyze(
        self,
        code: str,
        filename: str = "main.swift",
        options: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        metrics = self.calculate_basic_metrics(code)
        issues: List[Issue] = []

        # 1. swiftc diagnostics if installed
        if self.is_tool_available("swiftc"):
            with tempfile.TemporaryDirectory() as tmpdir:
                swift_file = os.path.join(tmpdir, "source.swift")
                with open(swift_file, "w", encoding="utf-8") as f:
                    f.write(code)

                cmd = ["swiftc", "-typecheck", swift_file]
                cmd_res = self.run_command(cmd, cwd=tmpdir, timeout=8)
                if cmd_res.stderr:
                    parsed = self._parse_swiftc_output(cmd_res.stderr)
                    issues.extend(parsed)

        # 2. Deep Swift Static Checks
        static_issues = self._run_static_swift_checks(code)
        issues.extend(static_issues)

        unique_issues = self._deduplicate_issues(issues)

        return AnalysisResult(
            language=self.language,
            filename=filename,
            status="completed",
            issues=unique_issues,
            complexity_metrics=metrics,
        )

    def _parse_swiftc_output(self, output: str) -> List[Issue]:
        issues: List[Issue] = []
        # Pattern: source.swift:line:col: error: message
        pattern = re.compile(r"^([^:]+):(\d+):(\d+):\s+(error|warning|note):\s+(.*)$", re.MULTILINE)
        for match in pattern.finditer(output):
            _, line_str, col_str, sev_str, msg = match.groups()
            line = int(line_str)
            col = int(col_str)
            severity = "Critical" if "error" in sev_str.lower() else "Medium"

            issues.append(
                Issue(
                    line=line,
                    column=col,
                    severity=severity,
                    type="Swift Diagnostic",
                    code="SWIFT-COMP-001",
                    message=msg.strip(),
                    source="swiftc",
                    suggestion="Fix Swift compiler diagnostic.",
                )
            )
        return issues

    def _run_static_swift_checks(self, code: str) -> List[Issue]:
        issues: List[Issue] = []
        lines = code.splitlines()

        for idx, line in enumerate(lines, start=1):
            trimmed = line.strip()
            if trimmed.startswith("//") or trimmed.startswith("/*"):
                continue

            # Check 1: Force unwrapping operator '!'
            if re.search(r'[a-zA-Z_]\w*!\.[a-zA-Z_]', line) or re.search(r'\bas!\s+', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("!") + 1,
                        severity="High",
                        type="Fatal Crash Hazard",
                        code="SWIFT-OPT-FORCE-UNWRAP",
                        message="Forced unwrapping with '!' or forced cast 'as!' triggers fatal runtime crash if value is nil.",
                        source="swift_static_analyzer",
                        suggestion="Use optional binding 'if let', 'guard let', or optional chaining '?.'.",
                    )
                )

            # Check 2: Forced try! expression
            if "try!" in line:
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("try!") + 1,
                        severity="High",
                        type="Fatal Error on Exception",
                        code="SWIFT-ERR-FORCE-TRY",
                        message="Forced 'try!' causes instant application crash if the throwing function throws an error.",
                        source="swift_static_analyzer",
                        suggestion="Use 'do { try ... } catch { ... }' or safe 'try?'.",
                    )
                )

            # Check 3: Closure retaining self without [weak self]
            if ("{ [weak self]" not in line and "{ [unowned self]" not in line) and \
               ("self." in line or "self?" in line) and \
               ("completion:" in line or "DispatchQueue." in line or "UIView.animate" in line):
                issues.append(
                    Issue(
                        line=idx,
                        column=1,
                        severity="Medium",
                        type="Memory Retain Cycle",
                        code="SWIFT-MEM-RETAIN-CYCLE",
                        message="Potential retain cycle / memory leak: closure strongly captures 'self'.",
                        source="swift_static_analyzer",
                        suggestion="Add capture list '[weak self]' at start of closure and unwrap with 'guard let self = self else { return }'.",
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
