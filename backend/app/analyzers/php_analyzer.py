"""PHP Language Analyzer.
Runs 'php -l' syntax check when installed,
paired with static analyzers for SQL injection, XSS, dangerous RCE functions (eval, system), and superglobal sanitization.
"""
import os
import re
import tempfile
from typing import Any, Dict, List, Optional
from app.analyzers.base import BaseAnalyzer, AnalysisResult, Issue


class PHPAnalyzer(BaseAnalyzer):
    language: str = "PHP"

    async def analyze(
        self,
        code: str,
        filename: str = "index.php",
        options: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        metrics = self.calculate_basic_metrics(code)
        issues: List[Issue] = []

        # 1. PHP Lint check (-l) if php CLI is installed
        if self.is_tool_available("php"):
            with tempfile.TemporaryDirectory() as tmpdir:
                php_file = os.path.join(tmpdir, "source.php")
                with open(php_file, "w", encoding="utf-8") as f:
                    f.write(code)

                cmd = ["php", "-l", php_file]
                cmd_res = self.run_command(cmd, cwd=tmpdir, timeout=6)
                if not cmd_res.success or "Errors parsing" in cmd_res.stdout or "PHP Parse error" in cmd_res.stderr:
                    raw = cmd_res.stdout + "\n" + cmd_res.stderr
                    parsed = self._parse_php_lint_output(raw)
                    if parsed:
                        issues.append(parsed)

        # 2. Deep PHP Static & OWASP Security Checks
        static_issues = self._run_static_php_checks(code)
        issues.extend(static_issues)

        unique_issues = self._deduplicate_issues(issues)

        return AnalysisResult(
            language=self.language,
            filename=filename,
            status="completed",
            issues=unique_issues,
            complexity_metrics=metrics,
        )

    def _parse_php_lint_output(self, output: str) -> Optional[Issue]:
        match = re.search(r"Parse error:\s*(.*?)\s+in\s+.*?\s+on line\s+(\d+)", output)
        if match:
            msg, line = match.groups()
            return Issue(
                line=int(line),
                column=1,
                severity="Critical",
                type="PHP Parse Error",
                code="PHP-SYNTAX-ERR",
                message=msg.strip(),
                source="php_lint",
                suggestion="Fix PHP syntax error on the flagged line.",
            )
        return None

    def _run_static_php_checks(self, code: str) -> List[Issue]:
        issues: List[Issue] = []
        lines = code.splitlines()

        for idx, line in enumerate(lines, start=1):
            trimmed = line.strip()
            if trimmed.startswith("//") or trimmed.startswith("#") or trimmed.startswith("/*"):
                continue

            # Check 1: SQL Injection via direct superglobal interpolation
            if re.search(r'\b(mysqli_query|mysql_query|pg_query|\$pdo->query|\$db->query)\s*\(.*\$_(GET|POST|REQUEST|COOKIE)', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=1,
                        severity="Critical",
                        type="SQL Injection",
                        code="PHP-SEC-SQLI",
                        message="SQL Injection vulnerability: unescaped superglobal variable used directly in SQL query.",
                        source="php_security_scanner",
                        suggestion="Use PDO prepared statements with parameter binding (e.g. '$stmt->execute([$param])').",
                    )
                )

            # Check 2: Reflected XSS via echo/print of unescaped superglobal
            if re.search(r'\b(echo|print)\s+.*\$_(GET|POST|REQUEST)\b', line) and "htmlspecialchars" not in line and "htmlentities" not in line:
                issues.append(
                    Issue(
                        line=idx,
                        column=1,
                        severity="High",
                        type="Cross-Site Scripting (XSS)",
                        code="PHP-SEC-XSS",
                        message="Reflected XSS vulnerability: user input from '$_GET/$_POST' printed directly to response without sanitization.",
                        source="php_security_scanner",
                        suggestion="Wrap output in 'htmlspecialchars($input, ENT_QUOTES, \"UTF-8\")'.",
                    )
                )

            # Check 3: Remote Code Execution / Command Injection via exec/system/eval
            if re.search(r'\b(eval|system|exec|passthru|shell_exec)\s*\(.*\$_(GET|POST|REQUEST)', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=1,
                        severity="Critical",
                        type="Remote Code Execution",
                        code="PHP-SEC-RCE",
                        message="Command Injection hazard: dangerous system/eval execution function receives unsanitized user input.",
                        source="php_security_scanner",
                        suggestion="Never pass user input to shell commands or 'eval()'; use 'escapeshellarg()' or safe native PHP APIs.",
                    )
                )

            # Check 4: Insecure Deserialization via unserialize()
            if re.search(r'\bunserialize\s*\(.*\$_(GET|POST|REQUEST|COOKIE)', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=1,
                        severity="Critical",
                        type="Insecure Deserialization",
                        code="PHP-SEC-UNSERIALIZE",
                        message="Insecure Deserialization: 'unserialize()' on untrusted user data allows PHP Object Injection and RCE.",
                        source="php_security_scanner",
                        suggestion="Use 'json_decode()' instead of 'unserialize()' for user-provided data.",
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
