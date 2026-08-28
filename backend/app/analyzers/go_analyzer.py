"""Go (Golang) Language Analyzer.
Runs 'go vet' and compiler diagnostics when installed,
paired with static analyzers for unhandled errors, goroutine loop variable races, unclosed HTTP bodies, and SQL injection.
"""
import os
import re
import tempfile
from typing import Any, Dict, List, Optional
from app.analyzers.base import BaseAnalyzer, AnalysisResult, Issue


class GoAnalyzer(BaseAnalyzer):
    language: str = "Go"

    async def analyze(
        self,
        code: str,
        filename: str = "main.go",
        options: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        metrics = self.calculate_basic_metrics(code)
        issues: List[Issue] = []

        # 1. Compiler diagnostics via 'go vet' if available
        if self.is_tool_available("go"):
            with tempfile.TemporaryDirectory() as tmpdir:
                go_file = os.path.join(tmpdir, "main.go")
                with open(go_file, "w", encoding="utf-8") as f:
                    f.write(code)

                # Initialize minimal go.mod in temp dir
                self.run_command(["go", "mod", "init", "tempmodule"], cwd=tmpdir, timeout=5)
                cmd = ["go", "vet", "."]
                cmd_res = self.run_command(cmd, cwd=tmpdir, timeout=8)
                if cmd_res.stderr:
                    parsed = self._parse_govet_output(cmd_res.stderr)
                    issues.extend(parsed)

        # 2. Deep Go Static & Concurrency Checks
        static_issues = self._run_static_go_checks(code)
        issues.extend(static_issues)

        unique_issues = self._deduplicate_issues(issues)

        return AnalysisResult(
            language=self.language,
            filename=filename,
            status="completed",
            issues=unique_issues,
            complexity_metrics=metrics,
        )

    def _parse_govet_output(self, output: str) -> List[Issue]:
        issues: List[Issue] = []
        # Pattern: ./main.go:line:col: message or main.go:line: message
        pattern = re.compile(r"(?:[.\/\\])?main\.go:(\d+)(?::(\d+))?:\s*(.*)$", re.MULTILINE)
        for match in pattern.finditer(output):
            line_str, col_str, msg = match.groups()
            line = int(line_str)
            col = int(col_str) if col_str else 0

            issues.append(
                Issue(
                    line=line,
                    column=col,
                    severity="High",
                    type="Go Vet Warning",
                    code="GO-VET-001",
                    message=msg.strip(),
                    source="go_vet",
                    suggestion="Fix go vet finding to ensure idiomatic and correct Go code.",
                )
            )
        return issues

    def _run_static_go_checks(self, code: str) -> List[Issue]:
        issues: List[Issue] = []
        lines = code.splitlines()

        for idx, line in enumerate(lines, start=1):
            trimmed = line.strip()
            if trimmed.startswith("//") or trimmed.startswith("/*"):
                continue

            # Check 1: Explicitly discarding error return (_ = fn() or val, _ := fn())
            if re.search(r'([a-zA-Z_]\w*),\s*_\s*:?=\s*[a-zA-Z_]\w*\.', line) or \
               re.search(r'_\s*=\s*(os\.Open|http\.Get|json\.Unmarshal|sql\.Open)\(', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("_") + 1,
                        severity="High",
                        type="Unhandled Error Return",
                        code="GO-ERR-IGNORED",
                        message="Ignoring returned error value with blank identifier ('_'). May lead to nil pointer dereference or silent failures.",
                        source="go_static_analyzer",
                        suggestion="Check error return: 'if err != nil { return err }'.",
                    )
                )

            # Check 2: Goroutine capturing loop variable
            if "for " in line and idx < len(lines):
                # Check for 'go func()' in the following loop body
                has_go_closure = False
                for look in lines[idx:min(len(lines), idx + 8)]:
                    if "go func()" in look or "go func ()" in look:
                        has_go_closure = True
                        break
                if has_go_closure:
                    issues.append(
                        Issue(
                            line=idx,
                            column=1,
                            severity="High",
                            type="Concurrency Race Hazard",
                            code="GO-RACE-LOOP-VAR",
                            message="Goroutine closures within loops capture loop variables by reference, causing race conditions.",
                            source="go_static_analyzer",
                            suggestion="Pass the loop variable as an explicit argument to the goroutine function.",
                        )
                    )

            # Check 3: SQL Injection via fmt.Sprintf in db query
            if re.search(r'\b(db\.Query|db\.QueryRow|db\.Exec)\s*\(.*fmt\.Sprintf', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=1,
                        severity="Critical",
                        type="SQL Injection",
                        code="GO-SEC-SQLI",
                        message="SQL Injection vulnerability: dynamically formatting query strings with 'fmt.Sprintf'.",
                        source="go_security_scanner",
                        suggestion="Use parameterized query placeholders ('$1' in PostgreSQL, '?' in MySQL/SQLite).",
                    )
                )

            # Check 4: HTTP response body not closed
            if "http.Get(" in line or "http.Post(" in line or "client.Do(" in line:
                # Check if defer resp.Body.Close() follows within next 4 lines
                has_close = False
                for look in lines[idx:min(len(lines), idx + 6)]:
                    if "Body.Close()" in look:
                        has_close = True
                        break
                if not has_close:
                    issues.append(
                        Issue(
                            line=idx,
                            column=1,
                            severity="High",
                            type="Resource Leak",
                            code="GO-RES-LEAK",
                            message="Unclosed HTTP response Body: missing 'defer resp.Body.Close()' leading to socket and goroutine leaks.",
                            source="go_static_analyzer",
                            suggestion="Add 'defer resp.Body.Close()' immediately after checking err == nil.",
                        )
                    )

            # Check 5: Division by literal zero
            div_zero = re.search(r"/\s*0\b(?!\.)", line)
            if div_zero and not line.strip().startswith("//"):
                issues.append(
                    Issue(
                        line=idx,
                        column=div_zero.start() + 1,
                        severity="Critical",
                        type="Division by Zero",
                        code="GO-LOGIC-DIVZERO",
                        message="Runtime Panic: integer division by zero.",
                        source="go_static_analyzer",
                        suggestion="Ensure divisor is non-zero before performing division.",
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
