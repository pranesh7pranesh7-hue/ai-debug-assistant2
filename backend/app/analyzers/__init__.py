"""BugSense AI Analyzer Registry.
Centralizes language analyzer instantiation, discovery, and dispatch.
"""
from typing import Dict, Optional
from app.analyzers.base import BaseAnalyzer
from app.analyzers.python_analyzer import PythonAnalyzer
from app.analyzers.c_analyzer import CAnalyzer
from app.analyzers.cpp_analyzer import CppAnalyzer
from app.analyzers.java_analyzer import JavaAnalyzer
from app.analyzers.javascript_analyzer import JavaScriptAnalyzer
from app.analyzers.typescript_analyzer import TypeScriptAnalyzer
from app.analyzers.csharp_analyzer import CSharpAnalyzer
from app.analyzers.go_analyzer import GoAnalyzer
from app.analyzers.rust_analyzer import RustAnalyzer
from app.analyzers.php_analyzer import PHPAnalyzer
from app.analyzers.kotlin_analyzer import KotlinAnalyzer
from app.analyzers.swift_analyzer import SwiftAnalyzer
from app.analyzers.ruby_analyzer import RubyAnalyzer
from app.analyzers.html_analyzer import HTMLAnalyzer
from app.analyzers.css_analyzer import CSSAnalyzer
from app.analyzers.sql_analyzer import SQLAnalyzer
from app.analyzers.shell_analyzer import ShellAnalyzer


# Singletons mapping canonical language name -> analyzer instance
ANALYZERS: Dict[str, BaseAnalyzer] = {
    "Python": PythonAnalyzer(),
    "C": CAnalyzer(),
    "C++": CppAnalyzer(),
    "Java": JavaAnalyzer(),
    "JavaScript": JavaScriptAnalyzer(),
    "TypeScript": TypeScriptAnalyzer(),
    "C#": CSharpAnalyzer(),
    "Go": GoAnalyzer(),
    "Rust": RustAnalyzer(),
    "PHP": PHPAnalyzer(),
    "Kotlin": KotlinAnalyzer(),
    "Swift": SwiftAnalyzer(),
    "Ruby": RubyAnalyzer(),
    "HTML": HTMLAnalyzer(),
    "CSS": CSSAnalyzer(),
    "SQL": SQLAnalyzer(),
    "Shell": ShellAnalyzer(),
}


def get_analyzer(language: str) -> BaseAnalyzer:
    """Retrieve analyzer instance for given language or fallback to Python."""
    if not language:
        return ANALYZERS["Python"]

    # Match case-insensitively
    lang_lower = language.strip().lower()
    for name, analyzer in ANALYZERS.items():
        if name.lower() == lang_lower:
            return analyzer

    # Fallback default
    return ANALYZERS["Python"]
