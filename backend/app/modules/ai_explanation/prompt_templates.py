"""AI Explanation Prompt Templates."""

EXPLANATION_SYSTEM_PROMPT = """You are BugSense AI, an expert polyglot software engineer, compiler diagnostics specialist, and security auditor.
Your job is to explain detected code bugs, compiler warnings, syntax errors, and security vulnerabilities clearly, accurately, and concisely.
Structure your explanation with 3 clear sections:
1. Root Cause: What is specifically wrong with this line of code and why it occurs in this programming language.
2. Runtime Impact: What will happen when this code executes or compiles in production (exceptions, memory corruption, crashes, data leaks).
3. Best Practice Fix: Concise guidance with idiomatic corrected code for this language.
"""


def build_explanation_prompt(
    code_snippet: str,
    line: int,
    tool: str,
    rule_id: str,
    category: str,
    message: str,
    language: str = "Python",
) -> str:
    """Build formatted prompt for bug explanation in any supported language."""
    lang_tag = language.lower().replace("+", "p").replace("#", "sharp")
    return f"""Please provide a thorough root-cause explanation for the following {language} code issue.

### Surrounding Code (Language: {language}, Around Line {line}):
```{lang_tag}
{code_snippet}
```

### Static Analysis Diagnostic:
- Programming Language: {language}
- Target Line: {line}
- Detection Tool: {tool}
- Rule Identifier: {rule_id}
- Issue Category: {category}
- Message: {message}

Explain what is wrong, why it occurs in {language}, and how to fix it according to {language} best practices.
"""

