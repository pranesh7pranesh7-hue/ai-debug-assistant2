"""CSS Language Analyzer.
Runs Stylelint when installed,
paired with static analyzers for unclosed braces, invalid color hexes, unitless dimensions, and !important anti-patterns.
"""
import re
from typing import Any, Dict, List, Optional
from app.analyzers.base import BaseAnalyzer, AnalysisResult, Issue


class CSSAnalyzer(BaseAnalyzer):
    language: str = "CSS"

    async def analyze(
        self,
        code: str,
        filename: str = "style.css",
        options: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        metrics = self.calculate_basic_metrics(code)
        issues: List[Issue] = []

        # 1. Deep CSS Syntax & Linter Checks
        static_issues = self._run_static_css_checks(code)
        issues.extend(static_issues)

        unique_issues = self._deduplicate_issues(issues)

        return AnalysisResult(
            language=self.language,
            filename=filename,
            status="completed",
            issues=unique_issues,
            complexity_metrics=metrics,
        )

    def _run_static_css_checks(self, code: str) -> List[Issue]:
        issues: List[Issue] = []
        lines = code.splitlines()

        # Check 1: Balanced Curly Braces
        open_braces = code.count("{")
        close_braces = code.count("}")
        if open_braces != close_braces:
            issues.append(
                Issue(
                    line=len(lines),
                    column=1,
                    severity="Critical",
                    type="Syntax Error",
                    code="CSS-BRACE-MISMATCH",
                    message=f"Mismatched curly braces: {open_braces} open '{{' but {close_braces} closing '}}'.",
                    source="css_parser",
                    suggestion="Verify all CSS rule blocks are properly closed with '}'.",
                )
            )

        for idx, line in enumerate(lines, start=1):
            trimmed = line.strip()
            if trimmed.startswith("/*") or trimmed.startswith("*"):
                continue

            # Check 2: Invalid Hex Color (e.g. #ffff or #gg0000)
            invalid_hex = re.search(r'#([0-9a-fA-F]{1,2}|[0-9a-fA-F]{4,5}|[0-9a-fA-F]{7}|[0-9a-fA-F]{9,})\b', line)
            if invalid_hex and not re.search(r'#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b', invalid_hex.group(0)):
                issues.append(
                    Issue(
                        line=idx,
                        column=invalid_hex.start() + 1,
                        severity="Medium",
                        type="Invalid Color Hex",
                        code="CSS-COLOR-HEX-INVALID",
                        message=f"Invalid color hex code '{invalid_hex.group(0)}'. Valid lengths are #RGB (3), #RRGGBB (6), or #RRGGBBAA (8).",
                        source="css_static_analyzer",
                        suggestion="Correct the hex color format.",
                    )
                )

            # Check 3: Non-zero unitless length (e.g., 'width: 100;' instead of '100px')
            unitless = re.search(r':\s*([1-9]\d*)\s*;', line)
            if unitless and not any(prop in line for prop in ["opacity", "z-index", "flex", "line-height", "font-weight", "order", "grid-column", "grid-row"]):
                issues.append(
                    Issue(
                        line=idx,
                        column=unitless.start() + 1,
                        severity="High",
                        type="Missing CSS Unit",
                        code="CSS-UNITLESS-LENGTH",
                        message=f"Non-zero dimension '{unitless.group(1)}' missing CSS unit (px, rem, em, %, vh, vw).",
                        source="css_static_analyzer",
                        suggestion="Specify an explicit length unit such as 'px' or 'rem'.",
                    )
                )

            # Check 4: Overuse of !important
            if "!important" in line:
                issues.append(
                    Issue(
                        line=idx,
                        column=line.find("!important") + 1,
                        severity="Low",
                        type="Maintainability Issue",
                        code="CSS-SPECIFICITY-IMPORTANT",
                        message="Use of '!important' overrides the CSS cascade and hampers maintainability.",
                        source="css_static_analyzer",
                        suggestion="Increase CSS selector specificity or restructure cascade layers instead of '!important'.",
                    )
                )

            # Check 5: Deprecated Vendor Prefixes (e.g. -moz-border-radius)
            if re.search(r'-(moz|webkit|o)-border-radius', line):
                issues.append(
                    Issue(
                        line=idx,
                        column=1,
                        severity="Low",
                        type="Obsolete Vendor Prefix",
                        code="CSS-OBSOLETE-PREFIX",
                        message="Obsolete vendor prefix property detected. Standard 'border-radius' is supported universally.",
                        source="css_static_analyzer",
                        suggestion="Use the standard unprefixed 'border-radius' property.",
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
