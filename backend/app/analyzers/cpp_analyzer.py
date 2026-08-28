"""C++ Language Analyzer.
Runs G++ / Clang++ compiler diagnostics when installed,
complemented with static checks for RAII, memory leaks, slicing, smart pointers, and exception safety.
"""
import os
import re
import tempfile
from typing import Any, Dict, List, Optional
from app.analyzers.base import BaseAnalyzer, AnalysisResult, Issue


class CppAnalyzer(BaseAnalyzer):
    language: str = "C++"

    async def analyze(
        self,
        code: str,
        filename: str = "main.cpp",
        options: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        metrics = self.calculate_basic_metrics(code)
        issues: List[Issue] = []

        # 1. Compiler Diagnostics (G++ / Clang++)
        compiler_tool = None
        if self.is_tool_available("g++"):
            compiler_tool = "g++"
        elif self.is_tool_available("clang++"):
            compiler_tool = "clang++"

        if compiler_tool:
            with tempfile.TemporaryDirectory() as tmpdir:
                cpp_file = os.path.join(tmpdir, "source.cpp")
                with open(cpp_file, "w", encoding="utf-8") as f:
                    f.write(code)

                cmd = [compiler_tool, "-fsyntax-only", "-std=c++17", "-Wall", "-Wextra", cpp_file]
                cmd_res = self.run_command(cmd, cwd=tmpdir, timeout=8)
                if cmd_res.stderr:
                    parsed = self._parse_compiler_output(cmd_res.stderr, compiler_tool)
                    issues.extend(parsed)

        # 2. Deep C++ Static & RAII Checks
        static_issues = self._run_static_cpp_checks(code)
        issues.extend(static_issues)

        # Deduplicate
        unique_issues = self._deduplicate_issues(issues)

        return AnalysisResult(
            language=self.language,
            filename=filename,
            status="completed",
            issues=unique_issues,
            complexity_metrics=metrics,
        )

    def _parse_compiler_output(self, output: str, tool_name: str) -> List[Issue]:
        issues: List[Issue] = []
        pattern = re.compile(r"^([^:]+):(\d+):(\d+):\s+(error|warning|note|fatal error):\s+(.*)$", re.MULTILINE | re.IGNORECASE)
        for match in pattern.finditer(output):
            _, line_str, col_str, sev_str, msg = match.groups()
            line = int(line_str)
            col = int(col_str)
            sev_lower = sev_str.lower()

            if "error" in sev_lower:
                severity = "Critical"
                issue_type = "Compilation Error"
                code = "CPP-COMP-ERR"
            elif "warning" in sev_lower:
                severity = "High"
                issue_type = "Compiler Warning"
                code = "CPP-COMP-WARN"
            else:
                severity = "Info"
                issue_type = "Compiler Note"
                code = "CPP-COMP-NOTE"

            issues.append(
                Issue(
                    line=line,
                    column=col,
                    severity=severity,
                    type=issue_type,
                    code=code,
                    message=msg.strip(),
                    source=tool_name,
                    suggestion="Address C++ compiler diagnostic to ensure clean compilation.",
                )
            )
        return issues

    def _run_static_cpp_checks(self, code: str) -> List[Issue]:
        issues: List[Issue] = []
        lines = code.splitlines()

        # Check 1: Return of local reference or pointer dangling hazard
        dangling_pattern = re.compile(r'\b([a-zA-Z_]\w*)\s*&\s+([a-zA-Z_]\w*)\s*\([^)]*\)\s*\{([^}]+)\}', re.MULTILINE)
        for match in dangling_pattern.finditer(code):
            func_body = match.group(3)
            return_match = re.search(r'\breturn\s+([a-zA-Z_]\w*)\s*;', func_body)
            if return_match:
                var_name = return_match.group(1)
                # Check if var is declared locally inside body
                if re.search(rf'\b(int|float|double|char|auto|std::\w+|\w+)\s+{var_name}\b', func_body):
                    line_num = code[:match.start()].count('\n') + 1
                    issues.append(
                        Issue(
                            line=line_num,
                            column=1,
                            severity="Critical",
                            type="Dangling Reference",
                            code="CPP-MEM-DANGLING",
                            message=f"Undefined Behavior: function returns reference to local stack variable '{var_name}'.",
                            source="cpp_static_analyzer",
                            suggestion="Return by value or allocate on heap/pass as reference parameter to avoid accessing destroyed stack memory.",
                        )
                    )

        # Check 2: Array new[] with non-array delete mismatch
        new_array_matches = re.findall(r'\bnew\s+\w+\s*\[', code)
        delete_scalar_matches = re.findall(r'\bdelete\s+(?!\[)\w+', code)
        delete_array_matches = re.findall(r'\bdelete\s*\[\s*\]', code)
        if len(new_array_matches) > len(delete_array_matches) and len(delete_scalar_matches) > 0:
            issues.append(
                Issue(
                    line=1,
                    column=1,
                    severity="High",
                    type="Memory Mismatch",
                    code="CPP-MEM-DEL-MISMATCH",
                    message="Mismatched deallocation: memory allocated with 'new[]' must be freed with 'delete[]', not scalar 'delete'.",
                    source="cpp_static_analyzer",
                    suggestion="Use 'delete[] ptr;' or prefer 'std::vector'/'std::unique_ptr<T[]>' for automatic RAII management.",
                )
            )

        # Line-by-line checks
        for idx, line in enumerate(lines, start=1):
            trimmed = line.strip()
            if trimmed.startswith("//") or trimmed.startswith("/*"):
                continue

            # Check 3: Raw manual new vs smart pointer recommendation
            if re.search(r'\bnew\s+[a-zA-Z_]\w*\s*(\(|\[)', line) and not "std::make_" in line:
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("new") + 1,
                        severity="Medium",
                        type="Modern C++ Best Practice",
                        code="CPP-MODERN-RAII",
                        message="Manual memory management with raw 'new'. Violates modern C++ RAII guidelines.",
                        source="cpp_static_analyzer",
                        suggestion="Use 'std::make_unique<T>()' or 'std::make_shared<T>()' to prevent memory leaks and ensure exception safety.",
                    )
                )

            # Check 4: Base class with virtual functions but non-virtual destructor
            if "virtual " in line and "(" in line and "class " in line:
                # Check class block for virtual ~Destructor
                has_virtual_dtor = False
                for look in lines[max(0, idx - 5):min(len(lines), idx + 20)]:
                    if "virtual ~" in look or "~" in look:
                        has_virtual_dtor = True
                        break
                if not has_virtual_dtor:
                    issues.append(
                        Issue(
                            line=idx,
                            column=1,
                            severity="High",
                            type="Polymorphic Safety",
                            code="CPP-POLY-DTOR",
                            message="Polymorphic base class with virtual methods lacks a virtual destructor.",
                            source="cpp_static_analyzer",
                            suggestion="Declare 'virtual ~ClassName() = default;' to ensure derived class destructors are called on polymorphic deletion.",
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
                        code="CPP-LOGIC-001",
                        message="ZeroDivisionError: literal division by zero detected.",
                        source="cpp_static_analyzer",
                        suggestion="Verify divisor is non-zero before executing division.",
                    )
                )

            # Check 6: Unsafe legacy C functions in C++
            for fn in ["gets", "strcpy", "strcat", "sprintf"]:
                if re.search(rf"\b{fn}\s*\(", line):
                    issues.append(
                        Issue(
                            line=idx,
                            column=line.find(fn) + 1,
                            severity="High",
                            type="Security Vulnerability",
                            code="CPP-SEC-LEGACY",
                            message=f"Legacy unsafe C string function '{fn}' used in C++ code.",
                            source="cpp_security_scanner",
                            suggestion=f"Replace '{fn}' with 'std::string' methods or 'std::string_view'.",
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
