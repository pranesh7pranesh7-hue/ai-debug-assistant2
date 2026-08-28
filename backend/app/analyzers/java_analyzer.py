"""Java Language Analyzer.
Runs javac compiler diagnostics when installed,
paired with static checks for NullPointerExceptions, unclosed streams, string equality (==), and SQL injection.
"""
import os
import re
import tempfile
from typing import Any, Dict, List, Optional
from app.analyzers.base import BaseAnalyzer, AnalysisResult, Issue


class JavaAnalyzer(BaseAnalyzer):
    language: str = "Java"

    async def analyze(
        self,
        code: str,
        filename: str = "Main.java",
        options: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        metrics = self.calculate_basic_metrics(code)
        issues: List[Issue] = []

        # 1. Compiler Diagnostics via javac if available
        if self.is_tool_available("javac"):
            # Extract public class name to match Java file requirements
            match_class = re.search(r'\bpublic\s+class\s+([a-zA-Z_]\w*)', code)
            class_name = match_class.group(1) if match_class else "Main"
            java_filename = f"{class_name}.java"

            with tempfile.TemporaryDirectory() as tmpdir:
                java_path = os.path.join(tmpdir, java_filename)
                with open(java_path, "w", encoding="utf-8") as f:
                    f.write(code)

                cmd = ["javac", "-Xlint:all", "-d", tmpdir, java_path]
                cmd_res = self.run_command(cmd, cwd=tmpdir, timeout=10)
                if cmd_res.stderr:
                    parsed = self._parse_javac_output(cmd_res.stderr, java_filename)
                    issues.extend(parsed)

        # 2. Deep Java Static & Semantic Checks
        static_issues = self._run_static_java_checks(code)
        issues.extend(static_issues)

        unique_issues = self._deduplicate_issues(issues)

        return AnalysisResult(
            language=self.language,
            filename=filename,
            status="completed",
            issues=unique_issues,
            complexity_metrics=metrics,
        )

    def _parse_javac_output(self, output: str, target_filename: str) -> List[Issue]:
        issues: List[Issue] = []
        # Pattern: Main.java:line: error: message
        pattern = re.compile(r"^([^:]+):(\d+):\s+(error|warning):\s+(.*)$", re.MULTILINE | re.IGNORECASE)
        for match in pattern.finditer(output):
            _, line_str, sev_str, msg = match.groups()
            line = int(line_str)
            sev_lower = sev_str.lower()
            severity = "Critical" if "error" in sev_lower else "High"
            code = "JAVA-COMP-ERR" if "error" in sev_lower else "JAVA-COMP-WARN"

            issues.append(
                Issue(
                    line=line,
                    column=0,
                    severity=severity,
                    type="Compilation Error" if "error" in sev_lower else "Compiler Warning",
                    code=code,
                    message=msg.strip(),
                    source="javac",
                    suggestion="Fix Java compiler issue to ensure class compiles successfully.",
                )
            )
        return issues

    def _run_static_java_checks(self, code: str) -> List[Issue]:
        issues: List[Issue] = []
        lines = code.splitlines()

        # Check Global: Unbalanced braces/parentheses
        open_braces = code.count("{")
        close_braces = code.count("}")
        if open_braces != close_braces:
            diff = abs(open_braces - close_braces)
            msg = f"Syntax Error: Unbalanced curly braces. Found {open_braces} '{{' and {close_braces} '}}'."
            issues.append(
                Issue(
                    line=len(lines),
                    column=1,
                    severity="Critical",
                    type="Syntax Error",
                    code="JAVA-SYNTAX-BRACES",
                    message=msg,
                    source="java_syntax_checker",
                    suggestion="Add the missing opening or closing brace '}' to balance class and method scopes.",
                )
            )

        for idx, line in enumerate(lines, start=1):
            trimmed = line.strip()
            if not trimmed or trimmed.startswith("//") or trimmed.startswith("/*") or trimmed.startswith("*"):
                continue

            # Check: 'else' without closing '}' on preceding 'if' block
            if trimmed.startswith("else"):
                # Look backwards for previous non-empty line
                prev_idx = idx - 2
                while prev_idx >= 0 and not lines[prev_idx].strip():
                    prev_idx -= 1
                if prev_idx >= 0:
                    prev_line = lines[prev_idx].strip()
                    if not prev_line.endswith("}") and not "}" in prev_line:
                        issues.append(
                            Issue(
                                line=idx,
                                column=line.find("else") + 1,
                                severity="Critical",
                                type="Syntax Error",
                                code="JAVA-SYNTAX-ELSE",
                                message="Syntax Error: 'else' without preceding closing brace '}' on 'if' block.",
                                source="java_syntax_checker",
                                suggestion="Insert '}' before 'else' to properly close the preceding 'if' block statement.",
                            )
                        )

            # Check: Unclosed parentheses in if/for/while headers
            if (trimmed.startswith("if") or trimmed.startswith("while") or trimmed.startswith("for")) and "(" in trimmed:
                if trimmed.count("(") != trimmed.count(")"):
                    issues.append(
                        Issue(
                            line=idx,
                            column=len(line),
                            severity="Critical",
                            type="Syntax Error",
                            code="JAVA-SYNTAX-PAREN",
                            message="Syntax Error: Unbalanced or unclosed parenthesis in control-flow condition header.",
                            source="java_syntax_checker",
                            suggestion="Ensure every '(' has a matching ')' in the condition header.",
                        )
                    )

            # Check: Missing Semicolon at end of standard statement lines
            # Applies to assignments, method invocations, returns, package/import statements, throws
            is_stmt = re.search(r'(=|\b(return|throw|System\.out\.println|import|package|int|double|float|long|boolean|char|byte|short|String|var)\b)', trimmed)
            is_header = any(trimmed.endswith(x) for x in ["{", "}", "(", ",", ":", "*/", "*/;"]) or trimmed.startswith("@") or trimmed.startswith("if") or trimmed.startswith("for") or trimmed.startswith("while") or trimmed.startswith("else") or trimmed.startswith("try") or trimmed.startswith("catch") or trimmed.startswith("class") or trimmed.startswith("interface") or trimmed.startswith("enum")
            if is_stmt and not is_header and not trimmed.endswith(";") and not trimmed.endswith("}"):
                issues.append(
                    Issue(
                        line=idx,
                        column=len(line),
                        severity="Critical",
                        type="Syntax Error",
                        code="JAVA-SYNTAX-SEMICOLON",
                        message="Syntax Error: Missing semicolon ';' at end of statement.",
                        source="java_syntax_checker",
                        suggestion="Add ';' at the end of the statement line.",
                    )
                )

            # Check: String comparison with '==' instead of '.equals()'
            str_eq = re.search(r'([a-zA-Z_]\w*|\"[^\"]*\")\s*==\s*([a-zA-Z_]\w*|\"[^\"]*\")', line)
            if str_eq and ('"' in line or "String" in line or "name" in line or "str" in line or "role" in line):
                left, right = str_eq.group(1), str_eq.group(2)
                if left.startswith('"') or right.startswith('"') or ("null" not in line and not left.isdigit() and not right.isdigit()):
                    issues.append(
                        Issue(
                            line=idx,
                            column=str_eq.start() + 1,
                            severity="High",
                            type="Equality Comparison Bug",
                            code="JAVA-LOGIC-STREQ",
                            message="String reference comparison with '==' instead of '.equals()'. May fail unexpectedly on identical content.",
                            source="java_static_analyzer",
                            suggestion="Use 'str1.equals(str2)' or 'Objects.equals(str1, str2)' for content comparison.",
                        )
                    )

            # Check: SQL Injection via String Concatenation in JDBC
            if re.search(r'\b(executeQuery|executeUpdate|prepareStatement)\s*\(.*(\+|\.concat\(|String\.format).*SELECT|INSERT|UPDATE|DELETE', line, re.IGNORECASE) or \
               (re.search(r'SELECT\s+.*FROM|UPDATE\s+.*SET|DELETE\s+FROM', line, re.IGNORECASE) and '"+' in line):
                issues.append(
                    Issue(
                        line=idx,
                        column=1,
                        severity="Critical",
                        type="SQL Injection",
                        code="JAVA-SEC-SQLI",
                        message="SQL Injection vulnerability: dynamic SQL constructed via string concatenation.",
                        source="java_security_scanner",
                        suggestion="Use parameterized queries with PreparedStatement placeholders ('?') instead of direct string concatenation.",
                    )
                )

            # Check: Resource Leak outside try-with-resources
            if re.search(r'\b(FileInputStream|FileOutputStream|BufferedReader|BufferedWriter|Scanner|Connection|Statement|ResultSet|Socket)\s+\w+\s*=\s*(new|\w+\.)', line):
                if not "try (" in line and not "try(" in line:
                    issues.append(
                        Issue(
                            line=idx,
                            column=1,
                            severity="High",
                            type="Resource Leak",
                            code="JAVA-RES-LEAK",
                            message="Unmanaged resource: Stream, Database Connection, Reader, or Socket instantiated outside of try-with-resources block.",
                            source="java_static_analyzer",
                            suggestion="Wrap resource allocation in 'try (ResourceType res = ...) { ... }' to guarantee deterministic closing.",
                        )
                    )

            # Check: Swallowed Exception / Empty Catch Block
            if re.search(r'catch\s*\(\s*(Exception|Throwable|\w+Exception)\s+\w+\s*\)\s*\{\s*\}', line) or \
               (line.strip().startswith("catch") and idx < len(lines) and lines[idx].strip() == "}"):
                issues.append(
                    Issue(
                        line=idx,
                        column=1,
                        severity="Medium",
                        type="Error Handling",
                        code="JAVA-ERR-SWALLOWED",
                        message="Empty catch block silently swallowing exceptions without logging or handling.",
                        source="java_static_analyzer",
                        suggestion="Log the exception with a logger (e.g. logger.error(...)) or rethrow as a custom runtime exception.",
                    )
                )

            # Check: Division by literal zero
            div_zero = re.search(r"/\s*0\b(?!\.)", line)
            if div_zero and not line.strip().startswith("//"):
                issues.append(
                    Issue(
                        line=idx,
                        column=div_zero.start() + 1,
                        severity="Critical",
                        type="Division by Zero",
                        code="JAVA-LOGIC-DIVZERO",
                        message="ArithmeticException: integer division or modulo by zero.",
                        source="java_static_analyzer",
                        suggestion="Guard division with a check ensuring divisor is not equal to zero.",
                    )
                )

            # Check: Calling toString() or methods on potentially null return
            if re.search(r'\.get\(\)\.|\.toString\(\)', line) and ("find" in line or "get(" in line or "map.get" in line):
                issues.append(
                    Issue(
                        line=idx,
                        column=1,
                        severity="Medium",
                        type="Null Safety",
                        code="JAVA-NULL-POINTER",
                        message="Potential NullPointerException: chaining method call on result that may return null.",
                        source="java_static_analyzer",
                        suggestion="Check for null before dereferencing or use Optional.ofNullable().",
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
