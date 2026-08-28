"""HTML Language Analyzer.
Runs standard HTML5 parser, accessibility checks (WCAG), deprecated tag detection, and XSS vector inspection.
"""
from html.parser import HTMLParser
import re
from typing import Any, Dict, List, Optional
from app.analyzers.base import BaseAnalyzer, AnalysisResult, Issue


class HTMLAuditParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.issues: List[Issue] = []
        self.tag_stack: List[tuple] = []
        self.has_title = False
        self.has_viewport = False
        self.void_tags = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
        self.deprecated_tags = {"font", "center", "marquee", "blink", "frame", "frameset", "big", "strike", "tt", "applet"}

    def handle_starttag(self, tag, attrs):
        lineno = self.getpos()[0]
        col = self.getpos()[1]
        attr_dict = dict(attrs)

        # 1. Deprecated tags
        if tag.lower() in self.deprecated_tags:
            self.issues.append(
                Issue(
                    line=lineno,
                    column=col,
                    severity="Medium",
                    type="Deprecated HTML Tag",
                    code="HTML-DEPRECATED-TAG",
                    message=f"Tag <{tag}> is obsolete and deprecated in HTML5.",
                    source="html_parser",
                    suggestion=f"Replace <{tag}> with modern semantic HTML5 tags and CSS styling.",
                )
            )

        # 2. Track tags on stack
        if tag.lower() not in self.void_tags:
            self.tag_stack.append((tag.lower(), lineno, col))

        # 3. Check <img> missing alt attribute
        if tag.lower() == "img" and "alt" not in attr_dict:
            self.issues.append(
                Issue(
                    line=lineno,
                    column=col,
                    severity="Low",
                    type="Accessibility (a11y)",
                    code="HTML-A11Y-IMG-ALT",
                    message="<img> element missing 'alt' attribute required for accessibility (WCAG).",
                    source="html_parser",
                    suggestion="Add a meaningful 'alt=\"...\"' description or 'alt=\"\"' for decorative images.",
                )
            )

        # 4. Check for inline javascript: URLs or dangerous inline events
        for attr, val in attrs:
            if val and val.lower().startswith("javascript:"):
                self.issues.append(
                    Issue(
                        line=lineno,
                        column=col,
                        severity="High",
                        type="XSS Vector",
                        code="HTML-SEC-JS-URI",
                        message=f"Attribute '{attr}' contains a 'javascript:' pseudo-protocol URI (potential XSS vector).",
                        source="html_security_scanner",
                        suggestion="Replace inline javascript: URI with an event listener in a separate script.",
                    )
                )

        if tag.lower() == "title":
            self.has_title = True

        if tag.lower() == "meta" and attr_dict.get("name", "").lower() == "viewport":
            self.has_viewport = True

    def handle_endtag(self, tag):
        tag_lower = tag.lower()
        if tag_lower in self.void_tags:
            return

        if self.tag_stack and self.tag_stack[-1][0] == tag_lower:
            self.tag_stack.pop()
        else:
            lineno = self.getpos()[0]
            col = self.getpos()[1]
            self.issues.append(
                Issue(
                    line=lineno,
                    column=col,
                    severity="Medium",
                    type="Unmatched Tag",
                    code="HTML-UNMATCHED-CLOSE",
                    message=f"Closing tag </{tag}> does not match open tag on stack.",
                    source="html_parser",
                    suggestion=f"Verify nesting and close open tags in correct LIFO order.",
                )
            )


class HTMLAnalyzer(BaseAnalyzer):
    language: str = "HTML"

    async def analyze(
        self,
        code: str,
        filename: str = "index.html",
        options: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        metrics = self.calculate_basic_metrics(code)
        issues: List[Issue] = []

        parser = HTMLAuditParser()
        try:
            parser.feed(code)
            issues.extend(parser.issues)

            # Check unclosed tags left on stack
            for unclosed_tag, line, col in parser.tag_stack:
                if unclosed_tag not in {"html", "body", "head"}:
                    issues.append(
                        Issue(
                            line=line,
                            column=col,
                            severity="Medium",
                            type="Unclosed HTML Tag",
                            code="HTML-UNCLOSED-TAG",
                            message=f"Unclosed HTML tag <{unclosed_tag}>.",
                            source="html_parser",
                            suggestion=f"Add closing </{unclosed_tag}> tag.",
                        )
                    )
        except Exception as e:
            issues.append(
                Issue(
                    line=1,
                    column=1,
                    severity="Critical",
                    type="HTML Parse Failure",
                    code="HTML-PARSE-ERR",
                    message=f"HTML parsing failed: {str(e)}",
                    source="html_parser",
                    suggestion="Check HTML for malformed structure.",
                )
            )

        # Static regex checks
        lines = code.splitlines()
        for idx, line in enumerate(lines, start=1):
            # Insecure http:// asset in script/link
            if re.search(r'<(script|link|iframe)[^>]+src=[\'"]http://', line, re.IGNORECASE):
                issues.append(
                    Issue(
                        line=idx,
                        column=1,
                        severity="High",
                        type="Mixed Content Security",
                        code="HTML-SEC-MIXED-CONTENT",
                        message="Insecure HTTP asset inclusion (mixed content hazard) in script/link/iframe.",
                        source="html_security_scanner",
                        suggestion="Use HTTPS ('https://') URLs for all external resources.",
                    )
                )

        unique_issues = self._deduplicate_issues(issues)

        return AnalysisResult(
            language=self.language,
            filename=filename,
            status="completed",
            issues=unique_issues,
            complexity_metrics=metrics,
        )

    def _deduplicate_issues(self, issues: List[Issue]) -> List[Issue]:
        seen = set()
        unique = []
        for i in issues:
            key = (i.line, i.code, i.message[:40])
            if key not in seen:
                seen.add(key)
                unique.append(i)
        return unique
