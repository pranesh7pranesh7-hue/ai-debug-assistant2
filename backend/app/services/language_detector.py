"""Language Detector Service for BugSense AI.
Detects programming languages from filenames, extensions, and source content heuristics.
Supports 17+ core programming languages.
"""
import re
from typing import Dict, List, Optional, Set, Tuple


class LanguageDetector:
    """Detects programming languages from extensions and source heuristics."""

    # Map extension -> Canonical Language Name
    EXTENSION_MAP: Dict[str, str] = {
        # Python
        ".py": "Python",
        ".pyw": "Python",
        ".wsgi": "Python",
        # C
        ".c": "C",
        # C++
        ".cpp": "C++",
        ".cc": "C++",
        ".cxx": "C++",
        ".hpp": "C++",
        ".hxx": "C++",
        ".hh": "C++",
        ".h++": "C++",
        # Java
        ".java": "Java",
        ".jav": "Java",
        # JavaScript
        ".js": "JavaScript",
        ".mjs": "JavaScript",
        ".cjs": "JavaScript",
        ".jsx": "JavaScript",
        # TypeScript
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".d.ts": "TypeScript",
        # C#
        ".cs": "C#",
        ".csx": "C#",
        # Go
        ".go": "Go",
        # Rust
        ".rs": "Rust",
        # PHP
        ".php": "PHP",
        ".phtml": "PHP",
        ".php3": "PHP",
        ".php4": "PHP",
        ".php5": "PHP",
        # Kotlin
        ".kt": "Kotlin",
        ".kts": "Kotlin",
        # Swift
        ".swift": "Swift",
        # Ruby
        ".rb": "Ruby",
        ".rake": "Ruby",
        ".gemspec": "Ruby",
        # HTML
        ".html": "HTML",
        ".htm": "HTML",
        ".xhtml": "HTML",
        # CSS
        ".css": "CSS",
        ".scss": "CSS",
        ".less": "CSS",
        ".sass": "CSS",
        # SQL
        ".sql": "SQL",
        ".ddl": "SQL",
        ".dml": "SQL",
        ".psql": "SQL",
        # Shell
        ".sh": "Shell",
        ".bash": "Shell",
        ".zsh": "Shell",
        ".ksh": "Shell",
        ".command": "Shell",
    }

    # Normalized canonical mapping for manual language strings
    NORMALIZED_NAMES: Dict[str, str] = {
        "python": "Python",
        "py": "Python",
        "c": "C",
        "c++": "C++",
        "cpp": "C++",
        "cxx": "C++",
        "java": "Java",
        "javascript": "JavaScript",
        "js": "JavaScript",
        "typescript": "TypeScript",
        "ts": "TypeScript",
        "c#": "C#",
        "csharp": "C#",
        "cs": "C#",
        "go": "Go",
        "golang": "Go",
        "rust": "Rust",
        "rs": "Rust",
        "php": "PHP",
        "kotlin": "Kotlin",
        "kt": "Kotlin",
        "swift": "Swift",
        "ruby": "Ruby",
        "rb": "Ruby",
        "html": "HTML",
        "htm": "HTML",
        "css": "CSS",
        "scss": "CSS",
        "less": "CSS",
        "sql": "SQL",
        "shell": "Shell",
        "bash": "Shell",
        "sh": "Shell",
        "zsh": "Shell",
    }

    SUPPORTED_LANGUAGES: List[str] = [
        "Python",
        "C",
        "C++",
        "Java",
        "JavaScript",
        "TypeScript",
        "C#",
        "Go",
        "Rust",
        "PHP",
        "Kotlin",
        "Swift",
        "Ruby",
        "HTML",
        "CSS",
        "SQL",
        "Shell",
    ]

    # Content-based patterns for ambiguous files
    CONTENT_HEURISTICS: List[Tuple[re.Pattern, str]] = [
        (re.compile(r"^#!\s*/.*\b(python|python3)\b", re.MULTILINE), "Python"),
        (re.compile(r"^#!\s*/.*\b(node|nodejs)\b", re.MULTILINE), "JavaScript"),
        (re.compile(r"^#!\s*/.*\b(bash|sh|zsh|dash)\b", re.MULTILINE), "Shell"),
        (re.compile(r"^#!\s*/.*\b(ruby)\b", re.MULTILINE), "Ruby"),
        (re.compile(r"^#!\s*/.*\b(php)\b", re.MULTILINE), "PHP"),
        (re.compile(r"^\s*<\?php", re.MULTILINE | re.IGNORECASE), "PHP"),
        (re.compile(r"<!DOCTYPE\s+html|<html\b|<head\b|<body\b", re.IGNORECASE), "HTML"),
        (re.compile(r"\bpublic\s+class\s+\w+|\bimport\s+java\.", re.MULTILINE), "Java"),
        (re.compile(r"\bpackage\s+main\b|\bfunc\s+(main|\w+\()", re.MULTILINE), "Go"),
        (re.compile(r"\bfn\s+main\s*\(\)|\buse\s+std::|\blet\s+mut\s+", re.MULTILINE), "Rust"),
        (re.compile(r"\busing\s+System(\.\w+)*;|\bnamespace\s+\w+", re.MULTILINE), "C#"),
        (re.compile(r"#include\s+<iostream>|\bstd::cout\b|\bstd::vector\b|\bnamespace\s+\w+\s*\{|\btemplate\s*<", re.MULTILINE), "C++"),
        (re.compile(r"#include\s+<stdio\.h>|#include\s+<stdlib\.h>|\bprintf\s*\(|\bmalloc\s*\(", re.MULTILINE), "C"),
        (re.compile(r"\bimport\s+SwiftUI|\bimport\s+UIKit|\bfunc\s+\w+\(.*\)\s*->", re.MULTILINE), "Swift"),
        (re.compile(r"\bfun\s+main\s*\(|\bval\s+\w+\s*:\s*\w+|\bvar\s+\w+\s*:\s*\w+", re.MULTILINE), "Kotlin"),
        (re.compile(r"\bdef\s+\w+.*end\b|\brequire_relative\b|\bputs\s+", re.MULTILINE), "Ruby"),
        (re.compile(r"\binterface\s+\w+\s*\{|\btype\s+\w+\s*=|\bas\s+const\b|:\s*(string|number|boolean|any)[\s;,]", re.MULTILINE), "TypeScript"),
        (re.compile(r"\bconsole\.log\(|\bconst\s+\w+\s*=|\blet\s+\w+\s*=|\bfunction\s+\w+\s*\(", re.MULTILINE), "JavaScript"),
        (re.compile(r"(@import|@media|\{\s*color:|\{\s*display:|\{\s*background:)", re.IGNORECASE), "CSS"),
        (re.compile(r"\b(SELECT\s+.*FROM|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|CREATE\s+TABLE)\b", re.IGNORECASE), "SQL"),
        (re.compile(r"\bdef\s+\w+\(.*\):|\bimport\s+\w+|\bfrom\s+\w+\s+import|\bclass\s+\w+(\(.*\))?:", re.MULTILINE), "Python"),
    ]

    @classmethod
    def detect_language(cls, filename: str = "code.py", code: Optional[str] = None) -> str:
        """Detect the programming language from a filename extension, with optional content-based fallback.

        Args:
            filename: The name or path of the file (used for extension matching).
            code: Optional source code string for content-based heuristic detection.

        Returns:
            Canonical language name (e.g. "Python", "JavaScript"), or "Unknown" if undetected.
        """
        lower_name = filename.lower()

        # 1. Special-case: TypeScript definition files
        if lower_name.endswith(".d.ts"):
            return "TypeScript"

        # 2. Extension-based detection
        ext = "." + lower_name.rsplit(".", 1)[-1] if "." in lower_name else ""
        lang = cls.EXTENSION_MAP.get(ext)

        # 3. Disambiguate .h headers between C and C++
        if lang == "C" and ext == ".h" and code:
            if cls._is_cpp_content(code):
                return "C++"

        if lang:
            return lang

        # 4. Content heuristics fallback
        if code:
            detected = cls._detect_from_content(code)
            if detected:
                return detected

        return "Unknown"

    @classmethod
    def _is_cpp_content(cls, code: str) -> bool:
        """Check if a .h header file contains C++ specific constructs."""
        cpp_indicators = [
            "class ", "template<", "template <", "std::", "namespace ",
            "public:", "private:", "protected:", "virtual ", "<vector>",
            "<string>", "<iostream>", "<memory>", "constexpr ", "noexcept"
        ]
        return any(ind in code for ind in cpp_indicators)

    @classmethod
    def _detect_from_content(cls, code: str) -> Optional[str]:
        """Match source code against content heuristics regex table."""
        sample = code[:4000]
        for pattern, lang in cls.CONTENT_HEURISTICS:
            if pattern.search(sample):
                return lang
        return None

    @classmethod
    def get_supported_extensions(cls) -> Set[str]:
        """Returns all recognized file extensions."""
        return set(cls.EXTENSION_MAP.keys())

    @classmethod
    def is_supported_file(cls, filename: str) -> bool:
        """Checks if a given filename has a supported extension."""
        lower_name = filename.lower()
        if lower_name.endswith(".d.ts"):
            return True
        ext = "." + lower_name.rsplit(".", 1)[-1] if "." in lower_name else ""
        return ext in cls.EXTENSION_MAP
