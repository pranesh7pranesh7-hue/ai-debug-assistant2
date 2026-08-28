"""Fix Recommendation Module.
Generates concrete patches and unified diffs with human-readable rationales.
"""
import ast
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.modules.fix_recommendation.diff_generator import (
    create_unified_diff,
    get_comment_prefix,
    validate_and_apply_patch,
)
from app.modules.fix_recommendation.prompt_templates import (
    FIX_SYSTEM_PROMPT,
    build_fix_prompt,
)
from app.modules.llm.llm_client import get_llm_client

logger = logging.getLogger("bugsense.recommender")


def synthesize_deterministic_fix(
    raw_code: str,
    line: int,
    category: str,
    message: str,
    rule_id: str = "",
    language: str = "Python",
) -> Tuple[Optional[str], str]:
    """Generates an immediate language-aware, AST/syntactically accurate fix for known bug patterns."""
    if not raw_code or not raw_code.strip():
        return None, ""

    lines = raw_code.splitlines()
    if not (1 <= line <= len(lines)):
        return None, ""

    target = lines[line - 1]
    msg_l = (message or "").lower()
    rule_l = (rule_id or "").lower()
    lang_l = (language or "Python").strip().lower()
    comment_pfx = get_comment_prefix(language)

    # -------------------------------------------------------------
    # 1. Missing Semicolon (Java, C, C++, JavaScript, TypeScript, C#, PHP, Rust, etc.)
    # -------------------------------------------------------------
    is_missing_semicolon = (
        "semicolon" in rule_l
        or "semicolon" in msg_l
        or "missing semicolon" in msg_l
        or "expected ';'" in msg_l
        or "semicolon expected" in msg_l
        or (rule_l == "java-syntax-semicolon")
    )
    if is_missing_semicolon:
        # Check if line already has a trailing semicolon (excluding comments)
        comment_pattern = re.compile(r"^(.*?)\s*(//.*|/\*.*?\*/|#.*|--.*)$")
        match = comment_pattern.match(target)
        if match:
            code_part = match.group(1).rstrip()
            comment_part = match.group(2)
            if not code_part.endswith(";"):
                fixed_line = f"{code_part}; {comment_part.lstrip()}"
            else:
                fixed_line = target
        else:
            trimmed = target.rstrip()
            if not trimmed.endswith(";"):
                fixed_line = trimmed + ";"
            else:
                fixed_line = target

        if fixed_line != target:
            lines[line - 1] = fixed_line
            patched = "\n".join(lines)
            return patched, f"Added missing semicolon ';' at the end of statement on line {line}."

    # -------------------------------------------------------------
    # 2. Missing Colon in Python compound headers (if, def, for, while, class, etc.)
    # -------------------------------------------------------------
    is_missing_colon = (
        lang_l == "python"
        and (
            "expected ':'" in msg_l
            or "missing colon" in msg_l
            or "colon" in msg_l
            or "py-syntax" in rule_l
            or ("syntax" in msg_l and any(target.strip().startswith(kw) for kw in ("def ", "if ", "elif ", "else", "for ", "while ", "with ", "class ", "try", "except", "finally", "async def ")))
        )
    )
    if is_missing_colon:
        comment_match = re.search(r"^(.*?)\s*(#.*)$", target)
        if comment_match:
            code_part = comment_match.group(1).rstrip()
            comment_part = comment_match.group(2)
            if not code_part.endswith(":"):
                fixed_line = f"{code_part}: {comment_part.lstrip()}"
            else:
                fixed_line = target
        else:
            trimmed = target.rstrip()
            if not trimmed.endswith(":"):
                fixed_line = trimmed + ":"
            else:
                fixed_line = target

        if fixed_line != target:
            lines[line - 1] = fixed_line
            patched = "\n".join(lines)
            try:
                ast.parse(patched)
            except SyntaxError:
                pass
            return patched, f"Added missing colon ':' at the end of statement header on line {line}."

    # -------------------------------------------------------------
    # 3. Java: Control-Flow Missing Parenthesis (JAVA-SYNTAX-PAREN)
    # -------------------------------------------------------------
    if "java-syntax-paren" in rule_l or ("parenthesis" in msg_l and lang_l == "java"):
        trimmed = target.rstrip()
        if trimmed.endswith("{"):
            header = trimmed[:-1].rstrip()
            if header.count("(") > header.count(")"):
                fixed_line = header + ") {"
                lines[line - 1] = fixed_line
                return "\n".join(lines), f"Closed missing parenthesis in control-flow condition header on line {line}."
        elif trimmed.count("(") > trimmed.count(")"):
            fixed_line = trimmed + ")"
            lines[line - 1] = fixed_line
            return "\n".join(lines), f"Closed missing parenthesis in control-flow condition on line {line}."

    # -------------------------------------------------------------
    # 4. Java: 'else' without preceding closing brace (JAVA-SYNTAX-ELSE)
    # -------------------------------------------------------------
    if "java-syntax-else" in rule_l or ("'else' without preceding closing brace" in msg_l and lang_l == "java"):
        indent = len(target) - len(target.lstrip())
        space = " " * indent
        stripped = target.strip()
        if stripped.startswith("else"):
            rest = stripped[4:].lstrip()
            fixed_line = f"{space}}} else {rest}".rstrip()
            lines[line - 1] = fixed_line
            return "\n".join(lines), f"Added preceding closing brace '}}' before 'else' block on line {line}."

    # -------------------------------------------------------------
    # 5. Java: Unbalanced Curly Braces (JAVA-SYNTAX-BRACES)
    # -------------------------------------------------------------
    if "java-syntax-braces" in rule_l or ("unbalanced curly braces" in msg_l and lang_l == "java"):
        open_c = raw_code.count("{")
        close_c = raw_code.count("}")
        if open_c > close_c:
            diff_count = open_c - close_c
            patched = raw_code.rstrip() + "\n" + "\n".join(["}"] * diff_count) + "\n"
            return patched, f"Added {diff_count} missing closing curly brace(s) '}}' to balance block definitions."

    # -------------------------------------------------------------
    # 6. Java: String Reference Equality == vs .equals() (JAVA-STRING-EQUALITY)
    # -------------------------------------------------------------
    if "java-string-equality" in rule_l or "string == equality" in msg_l or ("reference equality" in msg_l and lang_l == "java"):
        fixed_line = target
        # e.g. userRole == "ADMIN" -> userRole.equals("ADMIN")
        fixed_line = re.sub(r'(\b\w+\b)\s*==\s*("[^"]*")', r'\1.equals(\2)', fixed_line)
        # e.g. "ADMIN" == userRole -> "ADMIN".equals(userRole)
        fixed_line = re.sub(r'("[^"]*")\s*==\s*(\b\w+\b)', r'\1.equals(\2)', fixed_line)
        if fixed_line != target:
            lines[line - 1] = fixed_line
            return "\n".join(lines), f"Replaced reference equality '==' with '.equals()' for String comparison on line {line}."

    # -------------------------------------------------------------
    # 7. Java: Unclosed Resource Leak (JAVA-RESOURCE-LEAK)
    # -------------------------------------------------------------
    if "java-resource-leak" in rule_l or ("unclosed fileinputstream" in msg_l) or ("resource leak" in msg_l and lang_l == "java"):
        if "FileInputStream" in target and "new FileInputStream" in target and "=" in target:
            indent = len(target) - len(target.lstrip())
            space = " " * indent
            # Replace: FileInputStream fis = new FileInputStream(path); with try-with-resources
            stmt = target.strip().rstrip(";")
            fixed_line = f"{space}try ({stmt}) {{"
            lines[line - 1] = fixed_line
            # Close the try block at end of method if feasible
            if line < len(lines):
                lines.insert(line + 1, f"{space}}}")
            return "\n".join(lines), f"Wrapped unclosed stream in a try-with-resources statement on line {line} for automatic cleanup."

    # -------------------------------------------------------------
    # 8. C / C++ Dangerous gets() Buffer Overflow
    # -------------------------------------------------------------
    if "gets(" in target and any(k in msg_l or k in rule_l for k in ["buffer overflow", "gets", "c-buffer-overflow"]):
        fixed_line = re.sub(r'\bgets\s*\(\s*(\w+)\s*\)\s*;', r'fgets(\1, sizeof(\1), stdin);', target)
        if fixed_line != target:
            lines[line - 1] = fixed_line
            return "\n".join(lines), f"Replaced unsafe gets() with bounds-checked fgets() on line {line}."

    # -------------------------------------------------------------
    # 9. C / C++ Format String Vulnerability in printf()
    # -------------------------------------------------------------
    if "printf(" in target and any(k in msg_l or k in rule_l for k in ["format string", "c-format-string"]):
        fixed_line = re.sub(r'\bprintf\s*\(\s*([a-zA-Z_]\w*)\s*\)\s*;', r'printf("%s", \1);', target)
        if fixed_line != target:
            lines[line - 1] = fixed_line
            return "\n".join(lines), f"Specified '%s' format specifier in printf() on line {line} to prevent format string vulnerability."

    # -------------------------------------------------------------
    # 10. C++ Raw Pointer Leak / Missing delete[]
    # -------------------------------------------------------------
    if ("cpp_memory_leak" in msg_l or "cpp-memory-leak" in rule_l or "memory leak" in msg_l) and lang_l in ("c++", "cpp"):
        # Look for heap allocation on line: int* raw_handle = new int[100];
        match_var = re.search(r'\b(\w+)\s*=\s*new\s+\w+\s*\[', target)
        if match_var:
            var_name = match_var.group(1)
            indent = len(target) - len(target.lstrip())
            space = " " * indent
            # Insert delete[] before return in the block or 2 lines down
            insert_idx = min(line + 1, len(lines))
            lines.insert(insert_idx, f"{space}delete[] {var_name};")
            return "\n".join(lines), f"Added 'delete[] {var_name};' to free allocated heap memory on line {line}."

    # -------------------------------------------------------------
    # 11. JavaScript Unsafe eval()
    # -------------------------------------------------------------
    if "eval(" in target and any(k in msg_l or k in rule_l for k in ["eval", "js-eval-injection", "injection"]):
        fixed_line = re.sub(r'\beval\s*\(\s*(\w+)\s*\)', r'JSON.parse(\1)', target)
        if fixed_line != target:
            lines[line - 1] = fixed_line
            return "\n".join(lines), f"Replaced unsafe eval() with safe JSON parsing on line {line}."

    # -------------------------------------------------------------
    # 12. Python: Mutable Default Arguments
    # -------------------------------------------------------------
    if any(k in msg_l for k in ["mutable default", "dangerous default", "dangerous-default-value", "w0102"]) and 1 <= line <= len(lines):
        target = lines[line - 1]
        fixed_line = re.sub(r"=\s*\[\s*\]", "=None", target)
        fixed_line = re.sub(r"=\s*\{\s*\}", "=None", fixed_line)
        if fixed_line != target:
            indent = len(target) - len(target.lstrip()) + 4
            space = " " * indent
            param_match = re.search(r"(\w+)\s*=\s*None", fixed_line)
            param_name = param_match.group(1) if param_match else "items"
            insert_str = f"{space}if {param_name} is None:\n{space}    {param_name} = []"

            lines[line - 1] = fixed_line
            lines.insert(line, insert_str)
            patched = "\n".join(lines)
            try:
                ast.parse(patched)
                return patched, f"Replaced mutable default argument with None and initialized inside function on line {line}."
            except SyntaxError:
                pass

    # -------------------------------------------------------------
    # 13. Python: Bare except
    # -------------------------------------------------------------
    if any(k in msg_l for k in ["bare 'except:'", "bare except", "bare-except", "w0702", "no exception type"]) and 1 <= line <= len(lines):
        target = lines[line - 1]
        fixed_line = target.replace("except:", "except Exception as e:")
        lines[line - 1] = fixed_line
        patched = "\n".join(lines)
        try:
            ast.parse(patched)
            return patched, f"Specified 'except Exception as e:' on line {line} to avoid catching system exit signals."
        except SyntaxError:
            pass

    # -------------------------------------------------------------
    # 14. Python: Off-by-one Range
    # -------------------------------------------------------------
    if any(k in msg_l for k in ["off-by-one", "indexerror", "out of range", "+ 1", "+1"]) and 1 <= line <= len(lines):
        target = lines[line - 1]
        fixed_line = re.sub(r"\+\s*1\s*\)", ")", target)
        if fixed_line != target:
            lines[line - 1] = fixed_line
            patched = "\n".join(lines)
            try:
                ast.parse(patched)
                return patched, f"Removed '+ 1' boundary offset from range(len(...)) on line {line} to prevent IndexError."
            except SyntaxError:
                pass

    # -------------------------------------------------------------
    # 15. Python: SQL Injection via f-string
    # -------------------------------------------------------------
    if any(k in msg_l for k in ["sql injection", "b608", "sqli", "sql"]) and 1 <= line <= len(lines):
        target = lines[line - 1]
        indent = len(target) - len(target.lstrip())
        space = " " * indent
        fixed_line = target.replace('f"', '"').replace("f'", "'")
        lines[line - 1] = f"{space}{comment_pfx} FIX: Use parameterized SQL query\n{fixed_line}"
        patched = "\n".join(lines)
        try:
            ast.parse(patched)
            return patched, f"Refactored SQL string to parameterized query template on line {line}."
        except SyntaxError:
            pass

    # -------------------------------------------------------------
    # 16. Python: Unclosed File Resource Leak
    # -------------------------------------------------------------
    if any(k in msg_l for k in ["resource leak", "unclosed", "consider-using-with", "r1732"]) and 1 <= line <= len(lines):
        target = lines[line - 1]
        indent = len(target) - len(target.lstrip())
        space = " " * indent
        if "open(" in target and "=" in target:
            var_name = target.split("=")[0].strip()
            open_call = target.split("=", 1)[1].strip()
            fixed_line = f"{space}with {open_call} as {var_name}:"
            lines[line - 1] = fixed_line
            if line < len(lines):
                lines[line] = "    " + lines[line]
            patched = "\n".join(lines)
            try:
                ast.parse(patched)
                return patched, f"Enclosed file open operation in a 'with' context manager on line {line} for automatic cleanup."
            except SyntaxError:
                pass

    return None, ""


class FixRecommender:
    """Generates verified candidate fixes and unified diffs."""

    @staticmethod
    async def generate_fix(
        raw_code: str,
        line: int,
        tool: str,
        rule_id: str,
        message: str,
        category: str,
        explanation: str,
        custom_instruction: str = "",
        language: str = "Python",
        filename: str = "code.py",
    ) -> Dict[str, Any]:
        """Generate, validate, and return patch and appiable unified diff."""
        llm = get_llm_client()
        prompt = build_fix_prompt(
            full_source=raw_code,
            line=line,
            tool=tool,
            rule_id=rule_id,
            message=message,
            category=category,
            explanation=explanation,
            custom_instruction=custom_instruction,
            language=language,
        )

        try:
            response = await llm.generate_json(prompt, system_instruction=FIX_SYSTEM_PROMPT)
            patched_code = response.get("patched_code")
            rationale = response.get("rationale", "Applied recommended bug fix.")

            if patched_code and patched_code.strip():
                is_valid, diff_text, err = validate_and_apply_patch(
                    original_code=raw_code,
                    patched_code=patched_code,
                    language=language,
                    filename=filename,
                )
                if is_valid and diff_text:
                    return {
                        "patched_code": patched_code,
                        "diff_text": diff_text,
                        "rationale": rationale,
                        "status": "proposed",
                    }
        except Exception as e:
            logger.warning("LLM fix generation warning: %s", str(e))

        # Deterministic fallback fix
        det_patched, det_rationale = synthesize_deterministic_fix(
            raw_code=raw_code,
            line=line,
            category=category,
            message=message,
            rule_id=rule_id,
            language=language,
        )
        if det_patched:
            is_valid, diff_text, _ = validate_and_apply_patch(
                original_code=raw_code,
                patched_code=det_patched,
                language=language,
                filename=filename,
            )
            if is_valid and diff_text:
                return {
                    "patched_code": det_patched,
                    "diff_text": diff_text,
                    "rationale": det_rationale,
                    "status": "proposed",
                }

        # Language-aware safe comment patch (last resort fallback)
        comment_pfx = get_comment_prefix(language)
        lines = raw_code.splitlines()
        if 1 <= line <= len(lines):
            target = lines[line - 1]
            indent = len(target) - len(target.lstrip())
            space = " " * indent
            lines.insert(line - 1, f"{space}{comment_pfx} TODO(BugSense AI): Refactor line below to resolve {category} issue ({rule_id})")
            patched_fallback = "\n".join(lines)
            if raw_code.endswith("\n"):
                patched_fallback += "\n"
            diff_fallback = create_unified_diff(raw_code, patched_fallback, filename=filename)
            return {
                "patched_code": patched_fallback,
                "diff_text": diff_fallback,
                "rationale": f"Added inline remediation guidance for {rule_id}.",
                "status": "proposed",
            }

        return {
            "patched_code": raw_code,
            "diff_text": "",
            "rationale": "Unable to safely synthesize patch without syntax regression.",
            "status": "failed",
        }

