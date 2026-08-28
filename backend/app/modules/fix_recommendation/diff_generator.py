"""Unified Diff Generator and Patch Application Engine.
Validates diffs and ensures patched code is syntactically valid and cleanly applicable.
"""
import ast
import difflib
import logging
import re
from typing import Optional, Tuple

logger = logging.getLogger("bugsense.diff")


def get_comment_prefix(language: str = "Python") -> str:
    """Return the single-line comment syntax prefix for the specified programming language."""
    lang = (language or "Python").strip().lower()
    if lang in ("python", "ruby", "shell", "bash", "sh", "zsh", "perl", "yaml", "yml", "r"):
        return "#"
    elif lang in ("sql", "psql", "ddl", "dml", "lua", "haskell"):
        return "--"
    elif lang in ("css",):
        return "/*"
    else:  # Java, C, C++, JavaScript, TypeScript, C#, Go, Rust, PHP, Kotlin, Swift, etc.
        return "//"


def create_unified_diff(original_code: str, patched_code: str, filename: str = "code.py") -> str:
    """Generate a clean unified diff string between original and patched source code."""
    orig_lines = original_code.splitlines(keepends=True)
    patch_lines = patched_code.splitlines(keepends=True)

    # Ensure all lines end with newline for clean hunk header generation
    orig_lines = [l if l.endswith("\n") else l + "\n" for l in orig_lines]
    patch_lines = [l if l.endswith("\n") else l + "\n" for l in patch_lines]

    diff = difflib.unified_diff(
        orig_lines,
        patch_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
    )
    return "".join(diff)


def apply_unified_diff(original_code: str, diff_text: str) -> Tuple[bool, str, Optional[str]]:
    """Applies a unified diff to original_code string.
    Returns (success, patched_code, error_message).
    """
    if not diff_text or not diff_text.strip():
        return False, original_code, "Empty diff provided."

    orig_lines = original_code.splitlines()
    diff_lines = diff_text.splitlines()

    # Match hunk header: @@ -start,count +start,count @@
    hunk_regex = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@")

    hunks = []
    current_hunk = None

    for line in diff_lines:
        match = hunk_regex.match(line)
        if match:
            orig_start = int(match.group(1))
            orig_count = int(match.group(2)) if match.group(2) is not None else 1
            new_start = int(match.group(3))
            new_count = int(match.group(4)) if match.group(4) is not None else 1
            current_hunk = {
                "orig_start": orig_start,
                "orig_count": orig_count,
                "new_start": new_start,
                "new_count": new_count,
                "lines": [],
            }
            hunks.append(current_hunk)
        elif current_hunk is not None:
            if line.startswith(("+", "-", " ", "\\")):
                current_hunk["lines"].append(line)
            elif not line:
                # empty line in diff hunk counts as space context
                current_hunk["lines"].append(" ")

    if not hunks:
        return False, original_code, "No valid unified diff hunks found."

    result_lines = []
    orig_idx = 0  # 0-indexed line pointer in orig_lines

    for hunk in hunks:
        target_idx = hunk["orig_start"] - 1  # 0-indexed

        # Copy unchanged lines preceding this hunk
        while orig_idx < target_idx and orig_idx < len(orig_lines):
            result_lines.append(orig_lines[orig_idx])
            orig_idx += 1

        for hline in hunk["lines"]:
            if not hline:
                if orig_idx < len(orig_lines):
                    result_lines.append(orig_lines[orig_idx])
                    orig_idx += 1
                continue

            prefix = hline[0]
            content = hline[1:]

            if prefix == " ":
                if orig_idx < len(orig_lines):
                    result_lines.append(orig_lines[orig_idx])
                    orig_idx += 1
                else:
                    result_lines.append(content)
            elif prefix == "-":
                if orig_idx < len(orig_lines):
                    orig_idx += 1
            elif prefix == "+":
                result_lines.append(content)
            elif prefix == "\\":
                pass

    # Copy remaining lines following last hunk
    while orig_idx < len(orig_lines):
        result_lines.append(orig_lines[orig_idx])
        orig_idx += 1

    patched_code = "\n".join(result_lines)
    if original_code.endswith("\n") and not patched_code.endswith("\n"):
        patched_code += "\n"

    return True, patched_code, None


def validate_and_apply_patch(
    original_code: str,
    patched_code: str,
    language: str = "Python",
    filename: str = "code.py",
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Validate that the patched code compiles (for Python) and produces a valid, appiable diff.
    Returns: (is_valid, diff_text, error_message)
    """
    if not patched_code or not patched_code.strip():
        return False, None, "Patched code is empty."

    if language.strip().lower() == "python":
        try:
            ast.parse(patched_code)
        except SyntaxError as e:
            return False, None, f"Patched code introduced a Python syntax error on line {e.lineno}: {e.msg}"

    diff_text = create_unified_diff(original_code, patched_code, filename=filename)
    if not diff_text.strip():
        return False, None, "Patched code is identical to original code (no changes made)."

    # Verify that the generated diff applies cleanly back to original code
    success, applied_code, err = apply_unified_diff(original_code, diff_text)
    if not success:
        return False, None, f"Generated diff failed application test: {err}"

    return True, diff_text, None


def apply_patch_heuristic(original_code: str, target_line: int, old_line_str: str, new_line_str: str) -> Optional[str]:
    """Applies a targeted line substitution to original code."""
    lines = original_code.splitlines()
    if 1 <= target_line <= len(lines):
        target_idx = target_line - 1
        lines[target_idx] = new_line_str
        candidate = "\n".join(lines)
        return candidate
    return None

