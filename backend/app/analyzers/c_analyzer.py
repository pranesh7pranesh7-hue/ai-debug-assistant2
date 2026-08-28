"""C Language Analyzer.
Executes GCC / Clang / MSVC compiler diagnostics when installed,
paired with static analyzers for memory safety, buffer overflows, and pointer hazards.
"""
import os
import re
import tempfile
from typing import Any, Dict, List, Optional
from app.analyzers.base import BaseAnalyzer, AnalysisResult, Issue


class CAnalyzer(BaseAnalyzer):
    language: str = "C"

    # Unsafe functions prone to buffer overflows
    UNSAFE_FUNCTIONS = {
        "gets": ("Critical", "C-SEC-001", "Function 'gets' is dangerously unsafe and cannot prevent buffer overflows. Use 'fgets' instead."),
        "strcpy": ("High", "C-SEC-002", "Function 'strcpy' does not check buffer bounds. Consider 'strncpy' or 'strlcpy'."),
        "strcat": ("High", "C-SEC-003", "Function 'strcat' may cause buffer overflow without bounds check. Use 'strncat'."),
        "sprintf": ("Medium", "C-SEC-004", "Function 'sprintf' is prone to buffer overflows. Prefer 'snprintf' with explicit buffer length."),
        "scanf": ("Medium", "C-SEC-005", "Unbounded '%s' format in 'scanf' can overflow destination buffer. Specify width like '%255s'."),
    }

    async def analyze(
        self,
        code: str,
        filename: str = "main.c",
        options: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        metrics = self.calculate_basic_metrics(code)
        issues: List[Issue] = []

        # 1. Compiler Diagnostics (GCC / Clang) if available
        compiler_tool = None
        if self.is_tool_available("gcc"):
            compiler_tool = "gcc"
        elif self.is_tool_available("clang"):
            compiler_tool = "clang"

        if compiler_tool:
            with tempfile.TemporaryDirectory() as tmpdir:
                c_file = os.path.join(tmpdir, "source.c")
                with open(c_file, "w", encoding="utf-8") as f:
                    f.write(code)

                cmd = [compiler_tool, "-fsyntax-only", "-Wall", "-Wextra", "-Wformat", "-Wuninitialized", c_file]
                cmd_res = self.run_command(cmd, cwd=tmpdir, timeout=8)
                if cmd_res.stderr:
                    parsed = self._parse_gcc_clang_output(cmd_res.stderr, c_file, compiler_tool)
                    issues.extend(parsed)

        # 2. Deep Static & Semantic Pattern Checks
        static_issues = self._run_static_c_checks(code)
        issues.extend(static_issues)

        # Deduplicate issues on same line and message
        unique_issues = self._deduplicate_issues(issues)

        return AnalysisResult(
            language=self.language,
            filename=filename,
            status="completed",
            issues=unique_issues,
            complexity_metrics=metrics,
        )

    def _parse_gcc_clang_output(self, output: str, target_file: str, tool_name: str) -> List[Issue]:
        issues: List[Issue] = []
        # Pattern: filename:line:column: severity: message
        pattern = re.compile(r"^([^:]+):(\d+):(\d+):\s+(error|warning|note|fatal error):\s+(.*)$", re.MULTILINE | re.IGNORECASE)
        for match in pattern.finditer(output):
            _, line_str, col_str, sev_str, msg = match.groups()
            line = int(line_str)
            col = int(col_str)
            sev_lower = sev_str.lower()

            if "error" in sev_lower:
                severity = "Critical"
                issue_type = "Compilation Error"
                code = "C-COMP-ERR"
            elif "warning" in sev_lower:
                severity = "High"
                issue_type = "Compiler Warning"
                code = "C-COMP-WARN"
            else:
                severity = "Info"
                issue_type = "Compiler Note"
                code = "C-COMP-NOTE"

            issues.append(
                Issue(
                    line=line,
                    column=col,
                    severity=severity,
                    type=issue_type,
                    code=code,
                    message=msg.strip(),
                    source=tool_name,
                    suggestion="Fix compiler diagnostic to ensure correct C compilation.",
                )
            )
        return issues

    def _run_static_c_checks(self, code: str) -> List[Issue]:
        issues: List[Issue] = []
        lines = code.splitlines()

        # Check 1: Unsafe C Standard Library functions
        for line_idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*"):
                continue

            for fn_name, (sev, rule, desc) in self.UNSAFE_FUNCTIONS.items():
                if re.search(rf"\b{fn_name}\s*\(", line):
                    col = line.find(fn_name) + 1
                    issues.append(
                        Issue(
                            line=line_idx,
                            column=col,
                            severity=sev,
                            type="Security Vulnerability",
                            code=rule,
                            message=desc,
                            source="c_security_scanner",
                            suggestion=f"Replace '{fn_name}' with a safe, bounds-checked alternative.",
                        )
                    )

            # Check 2: Format String Vulnerability (printf(var) instead of printf("%s", var))
            fmt_match = re.search(r'\b(printf|fprintf|sprintf)\s*\(\s*([a-zA-Z_]\w*)\s*\)', line)
            if fmt_match and not '"' in fmt_match.group(0):
                issues.append(
                    Issue(
                        line=line_idx,
                        column=fmt_match.start() + 1,
                        severity="Critical",
                        type="Format String Injection",
                        code="C-SEC-FMT",
                        message="Potential Format String Vulnerability: dynamic variable passed directly as format string parameter.",
                        source="c_security_scanner",
                        suggestion="Always pass a constant format string literal like 'printf(\"%s\", var)' to prevent arbitrary memory reads/writes.",
                    )
                )

            # Check 3: Division by literal zero
            div_zero = re.search(r"/\s*0\b(?!\.)", line)
            if div_zero and not line.strip().startswith("//"):
                issues.append(
                    Issue(
                        line=line_idx,
                        column=div_zero.start() + 1,
                        severity="Critical",
                        type="Division by Zero",
                        code="C-LOGIC-001",
                        message="ZeroDivisionError: literal division by zero detected.",
                        source="c_static_analyzer",
                        suggestion="Check divisor before division to avoid runtime arithmetic exception.",
                    )
                )

            # Check 4: Assignment in if-condition (if (x = 5))
            if_assign = re.search(r'\bif\s*\(\s*([a-zA-Z_]\w*)\s*=\s*([^=][^)]*)\)', line)
            if if_assign and not "==" in if_assign.group(0):
                issues.append(
                    Issue(
                        line=line_idx,
                        column=if_assign.start() + 1,
                        severity="High",
                        type="Logic Defect",
                        code="C-LOGIC-002",
                        message=f"Possible unintentional assignment in if-condition statement: 'if ({if_assign.group(1)} = ...)'.",
                        source="c_static_analyzer",
                        suggestion="Use the equality comparison operator '==' instead of assignment '=' inside conditions.",
                    )
                )

            # Check 5: Unchecked malloc/calloc return value
            if re.search(r'\b(malloc|calloc|realloc)\s*\(', line):
                # Check next 3 lines for NULL check
                has_null_check = False
                for lookahead in lines[line_idx:min(len(lines), line_idx + 4)]:
                    if "NULL" in lookahead or "!" in lookahead:
                        has_null_check = True
                        break
                if not has_null_check and len(lines) > line_idx:
                    issues.append(
                        Issue(
                            line=line_idx,
                            column=line.find("alloc") + 1,
                            severity="Medium",
                            type="Memory Safety",
                            code="C-MEM-001",
                            message="Memory allocation via malloc/calloc without immediate NULL return-value check.",
                            source="c_static_analyzer",
                            suggestion="Check if the returned pointer is NULL before dereferencing to prevent crashes on out-of-memory.",
                        )
                    )

        # Check 6: Memory Leak check (malloc without free)
        malloc_count = len(re.findall(r'\b(malloc|calloc)\s*\(', code))
        free_count = len(re.findall(r'\bfree\s*\(', code))
        if malloc_count > free_count:
            issues.append(
                Issue(
                    line=1,
                    column=1,
                    severity="High",
                    type="Resource Leak",
                    code="C-MEM-LEAK",
                    message=f"Potential Memory Leak: {malloc_count} dynamic allocations found but only {free_count} free() calls in file.",
                    source="c_static_analyzer",
                    suggestion="Ensure every allocated buffer is released with free() in all exit paths.",
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
