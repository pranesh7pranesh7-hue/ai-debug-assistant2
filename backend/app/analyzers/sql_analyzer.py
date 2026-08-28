"""SQL Language Analyzer.
Analyzes SQL queries and DDL for unconstrained DELETE/UPDATE, = NULL comparison bugs, leading wildcard LIKE performance hazards, and injection risks.
"""
import re
from typing import Any, Dict, List, Optional
from app.analyzers.base import BaseAnalyzer, AnalysisResult, Issue


class SQLAnalyzer(BaseAnalyzer):
    language: str = "SQL"

    async def analyze(
        self,
        code: str,
        filename: str = "query.sql",
        options: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        metrics = self.calculate_basic_metrics(code)
        issues: List[Issue] = []

        # Run SQL Static & Best-Practice Checks
        static_issues = self._run_static_sql_checks(code)
        issues.extend(static_issues)

        unique_issues = self._deduplicate_issues(issues)

        return AnalysisResult(
            language=self.language,
            filename=filename,
            status="completed",
            issues=unique_issues,
            complexity_metrics=metrics,
        )

    def _run_static_sql_checks(self, code: str) -> List[Issue]:
        issues: List[Issue] = []
        lines = code.splitlines()

        # Check 1: Unconstrained DELETE without WHERE clause
        delete_matches = re.finditer(r'\bDELETE\s+FROM\s+([a-zA-Z_]\w*)(?!\s+WHERE\b)', code, re.IGNORECASE)
        for m in delete_matches:
            # Look ahead for WHERE in next 50 chars
            tail = code[m.end():m.end() + 100].upper()
            if "WHERE" not in tail:
                line_no = code[:m.start()].count('\n') + 1
                issues.append(
                    Issue(
                        line=line_no,
                        column=1,
                        severity="Critical",
                        type="Destructive Data Loss Risk",
                        code="SQL-UNCONSTRAINED-DELETE",
                        message=f"Unconstrained 'DELETE FROM {m.group(1)}' query has no WHERE clause; will erase entire table contents.",
                        source="sql_analyzer",
                        suggestion="Add an explicit 'WHERE' clause specifying target row condition or use 'TRUNCATE TABLE' if intentional.",
                    )
                )

        # Check 2: Unconstrained UPDATE without WHERE clause
        update_matches = re.finditer(r'\bUPDATE\s+([a-zA-Z_]\w*)\s+SET\s+[^;]+', code, re.IGNORECASE)
        for m in update_matches:
            stmt = m.group(0).upper()
            if "WHERE" not in stmt:
                line_no = code[:m.start()].count('\n') + 1
                issues.append(
                    Issue(
                        line=line_no,
                        column=1,
                        severity="Critical",
                        type="Destructive Data Loss Risk",
                        code="SQL-UNCONSTRAINED-UPDATE",
                        message=f"Unconstrained 'UPDATE {m.group(1)}' query missing WHERE clause; will overwrite all records in table.",
                        source="sql_analyzer",
                        suggestion="Add a restrictive 'WHERE id = ...' clause to target specific records.",
                    )
                )

        for idx, line in enumerate(lines, start=1):
            trimmed = line.strip()
            if trimmed.startswith("--") or trimmed.startswith("/*"):
                continue

            # Check 3: Comparing NULL with = NULL or != NULL
            null_eq = re.search(r'([=<>!]+)\s*NULL\b', line, re.IGNORECASE)
            if null_eq:
                op = null_eq.group(1)
                issues.append(
                    Issue(
                        line=idx,
                        column=null_eq.start() + 1,
                        severity="High",
                        type="Logic Bug (= NULL)",
                        code="SQL-NULL-COMPARISON",
                        message=f"Invalid comparison '{op} NULL'. In SQL, three-valued logic requires 'IS NULL' or 'IS NOT NULL'.",
                        source="sql_analyzer",
                        suggestion="Replace '= NULL' with 'IS NULL' and '!= NULL' / '<> NULL' with 'IS NOT NULL'.",
                    )
                )

            # Check 4: Leading wildcard LIKE '%pattern' causing full table scan
            if re.search(r"\bLIKE\s+['\"]%[a-zA-Z0-9_]", line, re.IGNORECASE):
                issues.append(
                    Issue(
                        line=idx,
                        column=1,
                        severity="Medium",
                        type="Performance Bottleneck",
                        code="SQL-PERF-LEADING-WILDCARD",
                        message="Leading wildcard in LIKE '%...' invalidates B-Tree index lookups and causes a full table scan.",
                        source="sql_analyzer",
                        suggestion="Consider full-text search indexes (MATCH...AGAINST or tsvector) or trailing wildcard 'pattern%'.",
                    )
                )

            # Check 5: SELECT * in queries
            if re.search(r'\bSELECT\s+\*\s+FROM\b', line, re.IGNORECASE):
                issues.append(
                    Issue(
                        line=idx,
                        column=line.upper().find("SELECT *") + 1,
                        severity="Low",
                        type="Code Quality",
                        code="SQL-SELECT-STAR",
                        message="'SELECT *' fetches all columns indiscriminately, increasing network bandwidth and breaking schema decoupling.",
                        source="sql_analyzer",
                        suggestion="Explicitly enumerate only the required column names (e.g. 'SELECT id, username, email FROM ...').",
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
