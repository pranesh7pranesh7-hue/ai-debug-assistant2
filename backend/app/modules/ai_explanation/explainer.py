"""AI Explanation Module.
Generates context-aware, plain-English explanations cached by bug signature.
"""
import logging
from typing import Dict, Optional

from app.modules.ai_explanation.prompt_templates import (
    EXPLANATION_SYSTEM_PROMPT,
    build_explanation_prompt,
)
from app.modules.llm.llm_client import get_llm_client
from app.modules.llm.token_utils import truncate_context
from app.utils.file_utils import compute_signature

logger = logging.getLogger("bugsense.explainer")

# In-memory explanation cache for identical signatures
_explanation_cache: Dict[str, str] = {}


def extract_context_snippet(raw_code: str, target_line: int, window: int = 8) -> str:
    """Extract code lines surrounding target line with line numbers."""
    lines = raw_code.splitlines()
    start = max(0, target_line - window - 1)
    end = min(len(lines), target_line + window)

    snippet_lines = []
    for idx in range(start, end):
        lineno = idx + 1
        marker = "--> " if lineno == target_line else "    "
        snippet_lines.append(f"{marker}{lineno:4d} | {lines[idx]}")

    return "\n".join(snippet_lines)


class BugExplainer:
    """Orchestrates AI explanations and caching."""

    @staticmethod
    async def explain_bug(
        raw_code: str,
        line: int,
        column: int,
        tool: str,
        rule_id: str,
        category: str,
        message: str,
        language: str = "Python",
    ) -> str:
        """Generate or retrieve cached plain-English explanation for a bug."""
        sig = compute_signature(line, column, rule_id, f"{language}:{message}")
        if sig in _explanation_cache:
            return _explanation_cache[sig]

        snippet = extract_context_snippet(raw_code, line)
        truncated_snippet = truncate_context(snippet, max_tokens=1500)

        prompt = build_explanation_prompt(
            code_snippet=truncated_snippet,
            line=line,
            tool=tool,
            rule_id=rule_id,
            category=category,
            message=message,
            language=language,
        )

        try:
            llm = get_llm_client()
            explanation = await llm.generate_text(
                prompt=prompt,
                system_instruction=EXPLANATION_SYSTEM_PROMPT,
            )
            _explanation_cache[sig] = explanation
            return explanation
        except Exception as e:
            logger.error("Explanation generation failure: %s", str(e))
            fallback = (
                f"### Root Cause\n"
                f"A {category} defect was flagged in {language} source by {tool} ({rule_id}): {message}.\n\n"
                f"### Runtime Impact\n"
                f"This condition may cause unexpected behavior, memory corruption, or runtime failures.\n\n"
                f"### Recommended Fix\n"
                f"Review line {line} and apply the recommended {language} fix pattern."
            )
            return fallback

