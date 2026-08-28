"""Prompt templates for AI Fix Recommendations."""

FIX_SYSTEM_PROMPT = """You are an automated software bug-fixing engineer.
Your task is to fix the reported bug cleanly and safely without changing the public API or introducing regressions.
CRITICAL REQUIREMENTS:
1. Return ONLY the complete, fully-patched source code inside standard markdown code block or JSON.
2. Provide a 1-2 sentence rationale explaining how the fix resolves the root cause.
"""


def build_fix_prompt(
    full_source: str,
    line: int,
    tool: str,
    rule_id: str,
    message: str,
    category: str,
    explanation: str,
    custom_instruction: str = "",
    language: str = "Python",
) -> str:
    """Build prompt requesting a precise patch for the target bug."""
    instruction_addon = f"\nAdditional Developer Guidance: {custom_instruction}\n" if custom_instruction else ""
    lang_tag = language.lower().replace("+", "p").replace("#", "sharp")

    return f"""Please fix the bug described below in the {language} source code.

### Target Bug Finding:
- Line Number: {line}
- Tool: {tool}
- Rule ID: {rule_id}
- Category: {category}
- Message: {message}
- Root Cause Explanation: {explanation}
{instruction_addon}
### Original {language} Source Code:
```{lang_tag}
{full_source}
```

Respond with a JSON object:
{{
  "rationale": "Clear explanation of how the patch fixes the issue",
  "patched_code": "The COMPLETE modified {language} code containing the fix"
}}
"""
