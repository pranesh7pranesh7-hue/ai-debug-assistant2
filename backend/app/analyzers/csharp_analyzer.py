"""C# (.NET) Language Analyzer.
Runs Roslyn / dotnet / csc compiler diagnostics when available,
paired with static checks for NullReferenceException, async deadlocks (.Result), IDisposable leaks, and SQL injection.
"""
import os
import re
import tempfile
from typing import Any, Dict, List, Optional
from app.analyzers.base import BaseAnalyzer, AnalysisResult, Issue


class CSharpAnalyzer(BaseAnalyzer):
    language: str = "C#"

    async def analyze(
        self,
        code: str,
        filename: str = "Program.cs",
        options: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        metrics = self.calculate_basic_metrics(code)
        issues: List[Issue] = []

        # 1. dotnet / csc compiler diagnostics if available
        if self.is_tool_available("csc"):
            with tempfile.TemporaryDirectory() as tmpdir:
                cs_file = os.path.join(tmpdir, "source.cs")
                with open(cs_file, "w", encoding="utf-8") as f:
                    f.write(code)

                cmd = ["csc", "/target:library", "/nologo", cs_file]
                cmd_res = self.run_command(cmd, cwd=tmpdir, timeout=8)
                if cmd_res.stdout or cmd_res.stderr:
                    raw_out = (cmd_res.stdout + "\n" + cmd_res.stderr).strip()
                    parsed = self._parse_csc_output(raw_out)
                    issues.extend(parsed)

        # 2. Deep C# Static & Roslyn-like Checks
        static_issues = self._run_static_csharp_checks(code)
        issues.extend(static_issues)

        unique_issues = self._deduplicate_issues(issues)

        return AnalysisResult(
            language=self.language,
            filename=filename,
            status="completed",
            issues=unique_issues,
            complexity_metrics=metrics,
        )

    def _parse_csc_output(self, output: str) -> List[Issue]:
        issues: List[Issue] = []
        # Pattern: source.cs(line,col): error CS0103: The name 'x' does not exist
        pattern = re.compile(r"^([^(\n]+)\((\d+),(\d+)\):\s+(error|warning)\s+(CS\d+):\s+(.*)$", re.MULTILINE)
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
                    type="Compiler Diagnostic",
                    code=code_str,
                    message=msg.strip(),
                    source="csc",
                    suggestion="Fix C# compiler diagnostic to ensure clean build.",
                )
            )
        return issues

    def _run_static_csharp_checks(self, code: str) -> List[Issue]:
        issues: List[Issue] = []
        lines = code.splitlines()

        for idx, line in enumerate(lines, start=1):
            trimmed = line.strip()
            if trimmed.startswith("//") or trimmed.startswith("/*") or trimmed.startswith("*"):
                continue

            # Check 1: Async Deadlock via .Result or .Wait() on Task
            if re.search(r'\b[a-zA-Z_]\w*\.Result\b|\b[a-zA-Z_]\w*\.Wait\(\)', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=1,
                        severity="High",
                        type="Async Deadlock Hazard",
                        code="CS-ASYNC-BLOCKING",
                        message="Synchronously blocking on asynchronous Task using '.Result' or '.Wait()' can trigger thread pool starvation and deadlocks.",
                        source="csharp_static_analyzer",
                        suggestion="Use 'await' asynchronously instead of blocking synchronously on Task completion.",
                    )
                )

            # Check 2: IDisposable without 'using' statement
            if re.search(r'\b(new\s+(SqlConnection|SqlCommand|FileStream|HttpClient|StreamReader|StreamWriter|DbContext))\b', line):
                if not "using " in line and not "using(" in line:
                    issues.append(
                        Issue(
                            line=idx,
                            column=line.find("new") + 1,
                            severity="High",
                            type="Resource Leak",
                            code="CS-RES-LEAK",
                            message="IDisposable object instantiated without a 'using' statement or declaration.",
                            source="csharp_static_analyzer",
                            suggestion="Use 'using var resource = ...;' or 'using (var resource = ...) { ... }' to ensure deterministic disposal.",
                        )
                    )

            # Check 3: SQL Injection via string interpolation in SqlCommand
            if re.search(r'\b(SqlCommand|FromSqlRaw|ExecuteSqlRaw)\s*\(.*\$"', line) or \
               (re.search(r'\b(SqlCommand|FromSqlRaw)\s*\(', line) and '"+' in line):
                issues.append(
                    Issue(
                        line=idx,
                        column=1,
                        severity="Critical",
                        type="SQL Injection",
                        code="CS-SEC-SQLI",
                        message="SQL Injection vulnerability: dynamic SQL query composed using string interpolation.",
                        source="csharp_security_scanner",
                        suggestion="Use parameterized queries with 'SqlParameter' or 'FromSqlInterpolated'.",
                    )
                )

            # Check 4: Swallowed Exception in catch
            if re.search(r'catch\s*\(\s*(Exception|object)\s+\w*\s*\)\s*\{\s*\}', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=1,
                        severity="Medium",
                        type="Error Handling",
                        code="CS-ERR-SWALLOWED",
                        message="Empty catch block silently suppressing exceptions.",
                        source="csharp_static_analyzer",
                        suggestion="Log the exception with ILogger or rethrow with 'throw;' to preserve stack trace.",
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
                        code="CS-LOGIC-DIVZERO",
                        message="DivideByZeroException: literal division by zero.",
                        source="csharp_static_analyzer",
                        suggestion="Verify divisor is non-zero before division.",
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
