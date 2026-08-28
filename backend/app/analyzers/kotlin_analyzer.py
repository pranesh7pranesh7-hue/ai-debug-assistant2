"""Kotlin Language Analyzer.
Runs kotlinc compiler diagnostics when installed,
paired with static analyzers for '!!' null assertion hazards, GlobalScope coroutine leaks, and unsafe type casting.
"""
import os
import re
import tempfile
from typing import Any, Dict, List, Optional
from app.analyzers.base import BaseAnalyzer, AnalysisResult, Issue


class KotlinAnalyzer(BaseAnalyzer):
    language: str = "Kotlin"

    async def analyze(
        self,
        code: str,
        filename: str = "Main.kt",
        options: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        metrics = self.calculate_basic_metrics(code)
        issues: List[Issue] = []

        # 1. kotlinc compiler diagnostics if installed
        if self.is_tool_available("kotlinc"):
            with tempfile.TemporaryDirectory() as tmpdir:
                kt_file = os.path.join(tmpdir, "source.kt")
                with open(kt_file, "w", encoding="utf-8") as f:
                    f.write(code)

                cmd = ["kotlinc", kt_file, "-d", tmpdir]
                cmd_res = self.run_command(cmd, cwd=tmpdir, timeout=10)
                if cmd_res.stderr:
                    parsed = self._parse_kotlinc_output(cmd_res.stderr)
                    issues.extend(parsed)

        # 2. Deep Kotlin Static Checks
        static_issues = self._run_static_kotlin_checks(code)
        issues.extend(static_issues)

        unique_issues = self._deduplicate_issues(issues)

        return AnalysisResult(
            language=self.language,
            filename=filename,
            status="completed",
            issues=unique_issues,
            complexity_metrics=metrics,
        )

    def _parse_kotlinc_output(self, output: str) -> List[Issue]:
        issues: List[Issue] = []
        # Pattern: source.kt:line:col: error: message
        pattern = re.compile(r"^([^:]+):(\d+):(\d+):\s+(error|warning):\s+(.*)$", re.MULTILINE)
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
                    type="Kotlin Diagnostic",
                    code="KT-COMP-001",
                    message=msg.strip(),
                    source="kotlinc",
                    suggestion="Address Kotlin compiler diagnostic.",
                )
            )
        return issues

    def _run_static_kotlin_checks(self, code: str) -> List[Issue]:
        issues: List[Issue] = []
        lines = code.splitlines()

        for idx, line in enumerate(lines, start=1):
            trimmed = line.strip()
            if trimmed.startswith("//") or trimmed.startswith("/*"):
                continue

            # Check 1: Non-null assertion operator '!!'
            if re.search(r'[a-zA-Z_]\w*!!(\.|\b)', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("!!") + 1,
                        severity="High",
                        type="Null Safety Hazard",
                        code="KT-NULL-ASSERTION",
                        message="Non-null assertion operator ('!!') will throw NullPointerException at runtime if variable is null.",
                        source="kotlin_static_analyzer",
                        suggestion="Use safe call '?.' or Elvis operator '?:' with a fallback value.",
                    )
                )

            # Check 2: GlobalScope.launch coroutine leak
            if "GlobalScope.launch" in line or "GlobalScope.async" in line:
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("GlobalScope") + 1,
                        severity="High",
                        type="Coroutine Lifecycle Leak",
                        code="KT-COROUTINE-GLOBALSCOPE",
                        message="Use of 'GlobalScope' bypasses structured concurrency and may cause memory and thread leaks.",
                        source="kotlin_static_analyzer",
                        suggestion="Use structured CoroutineScope (e.g. viewModelScope, lifecycleScope, or coroutineScope { }).",
                    )
                )

            # Check 3: Thread.sleep inside coroutine
            if "Thread.sleep(" in line:
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("Thread.sleep") + 1,
                        severity="Medium",
                        type="Thread Blocking Hazard",
                        code="KT-COROUTINE-BLOCKING",
                        message="Blocking thread call 'Thread.sleep()' detected. In coroutines, this blocks the underlying dispatcher thread.",
                        source="kotlin_static_analyzer",
                        suggestion="Replace 'Thread.sleep()' with non-blocking suspend function 'delay()'.",
                    )
                )

            # Check 4: Unsafe type casting 'as' instead of 'as?'
            if re.search(r'\bas\s+(?!\?)[A-Z]\w*', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("as") + 1,
                        severity="Medium",
                        type="Unsafe Cast",
                        code="KT-TYPE-UNSAFE-CAST",
                        message="Unsafe type cast 'as' will throw ClassCastException if the target type does not match.",
                        source="kotlin_static_analyzer",
                        suggestion="Use safe cast 'as?' combined with Elvis operator '?:' for error handling.",
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
