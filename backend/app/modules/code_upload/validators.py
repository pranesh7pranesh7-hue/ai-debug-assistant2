"""Code upload validators: AST pre-check, file size/type constraints, and UTF-8 verification."""
import ast
from typing import Optional, Tuple

from app.config import get_settings
from app.core.exceptions import CodeSyntaxError, ValidationError


import re


def normalize_code(raw_code: str, filename: str = "code.py", language: Optional[str] = None) -> str:
    """Normalize code by removing surrounding markdown code fences.
    For Python, also tries to remove line-number prefixes.
    """
    if not raw_code:
        return ""

    code = raw_code.strip()

    if code.startswith("```"):
        lines = code.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].strip().startswith("```"):
            code = "\n".join(lines[1:-1]).strip()
        elif len(lines) >= 1 and lines[0].startswith("```"):
            code = "\n".join(lines[1:]).strip()

    from app.services.language_detector import LanguageDetector
    is_python = (language.strip().lower() == "python") if (language and language.strip().lower() not in ("auto", "unknown", "")) else (LanguageDetector.detect_language(filename=filename, code=code) == "Python")
    if not is_python:
        return code

    # 2. Check if code already parses directly as valid Python
    try:
        ast.parse(code)
        return code
    except SyntaxError:
        pass

    # 3. Check if all non-empty lines have line-number prefixes (e.g. copied from IDE/editor)
    lines = code.splitlines()
    non_empty = [l for l in lines if l.strip()]
    if non_empty:
        # Format A: Colon / Pipe / Tab separator: e.g. "44:    def foo():" or "44 |    def foo():"
        pattern_sep = re.compile(r"^\s*\d+[:\|\t]\s?(.*)$")
        matches_sep = [pattern_sep.match(l) for l in non_empty]
        if all(m is not None for m in matches_sep):
            candidate_lines = []
            for l in lines:
                if not l.strip():
                    candidate_lines.append("")
                else:
                    m = pattern_sep.match(l)
                    candidate_lines.append(m.group(1) if m else l)
            candidate = "\n".join(candidate_lines)
            try:
                ast.parse(candidate)
                return candidate
            except SyntaxError:
                pass

        # Format B: Space-separated line numbers: e.g. "44  def foo():"
        pattern_space = re.compile(r"^(\s*\d+)(\s+)(.*)$")
        matches_space = [pattern_space.match(l) for l in non_empty]
        if all(m is not None for m in matches_space):
            min_sep_len = min(len(m.group(2)) for m in matches_space)
            candidate_lines = []
            for l in lines:
                if not l.strip():
                    candidate_lines.append("")
                else:
                    m = pattern_space.match(l)
                    if m:
                        spaces = m.group(2)
                        rest = m.group(3)
                        kept_indent = spaces[min_sep_len:]
                        candidate_lines.append(kept_indent + rest)
                    else:
                        candidate_lines.append(l)
            candidate = "\n".join(candidate_lines)
            try:
                ast.parse(candidate)
                return candidate
            except SyntaxError:
                pass

    return code


def validate_code_syntax(raw_code: str, filename: str = "code.py", language: Optional[str] = None) -> Tuple[bool, str]:
    """Validate that the raw code is valid syntax (checks AST for Python)."""
    if not raw_code or not raw_code.strip():
        raise ValidationError(message="Uploaded code cannot be empty.")

    normalized = normalize_code(raw_code, filename=filename, language=language)

    from app.services.language_detector import LanguageDetector
    is_python = (language.strip().lower() == "python") if (language and language.strip().lower() not in ("auto", "unknown", "")) else (LanguageDetector.detect_language(filename=filename, code=normalized) == "Python")
    if not is_python:
        return True, "Syntax valid (not checked for non-Python)."

    try:
        ast.parse(normalized, filename=filename)
        return True, "Valid Python syntax."
    except SyntaxError as e:
        raise CodeSyntaxError(
            message=f"Python syntax error on line {e.lineno}, column {e.offset}: {e.msg}",
            line=e.lineno,
            details={
                "text": e.text.strip() if e.text else "",
                "filename": filename,
                "column": e.offset,
                "error_type": "SyntaxError",
                "message": e.msg,
            },
        )


def validate_python_code(raw_code: str, filename: str = "code.py", language: Optional[str] = "Python") -> Tuple[bool, str]:
    """Alias for validate_code_syntax for backward compatibility."""
    return validate_code_syntax(raw_code, filename=filename, language=language)


def normalize_python_code(raw_code: str, filename: str = "code.py", language: Optional[str] = "Python") -> str:
    """Alias for normalize_code for Python."""
    return normalize_code(raw_code, filename=filename, language=language)


def validate_file_size(size_bytes: int) -> None:
    """Validate uploaded file size against configured MAX_UPLOAD_SIZE_MB."""
    settings = get_settings()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        raise ValidationError(
            message=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
            details={"size_bytes": size_bytes, "max_bytes": max_bytes},
        )


from app.services.language_detector import LanguageDetector

def validate_file_extension(filename: str) -> None:
    """Validate that the file has a permitted extension."""
    allowed = LanguageDetector.get_supported_extensions() | {".zip"}
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in allowed:
        raise ValidationError(
            message=f"Unsupported file format '{ext}'. Allowed extensions: {', '.join(sorted(allowed))}",
            details={"allowed_extensions": list(allowed), "filename": filename},
        )
