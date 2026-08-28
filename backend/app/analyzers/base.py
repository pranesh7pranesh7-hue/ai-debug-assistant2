"""Base Analyzer Definition for BugSense AI Multi-Language Analysis System.
All language analyzers implement BaseAnalyzer and output standardized AnalysisResult structures.
"""
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional


@dataclass
class Issue:
    """Standardized issue finding across all languages."""
    line: int = 1
    column: int = 0
    severity: str = "Medium"  # Critical, High, Medium, Low, Info
    type: str = "General"
    code: str = "BUG-000"
    message: str = ""
    source: str = "static_analyzer"
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisResult:
    """Standardized analysis output across all languages."""
    language: str
    filename: str
    status: str = "completed"  # completed, analyzer_unavailable, syntax_error, unsupported
    issues: List[Issue] = field(default_factory=list)
    issues_found: int = 0
    complexity_metrics: Dict[str, Any] = field(default_factory=dict)
    summary_message: Optional[str] = None

    def __post_init__(self):
        self.issues_found = len(self.issues)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "language": self.language,
            "filename": self.filename,
            "status": self.status,
            "issues_found": len(self.issues),
            "issues": [i.to_dict() for i in self.issues],
            "complexity_metrics": self.complexity_metrics,
            "summary_message": self.summary_message,
        }


class BaseAnalyzer(ABC):
    """Abstract base class for all language-specific analyzers."""

    language: str = "Generic"

    @abstractmethod
    async def analyze(
        self,
        code: str,
        filename: str = "code",
        options: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        """Run language analysis and return standardized AnalysisResult."""
        pass

    @staticmethod
    def is_tool_available(tool_name: str) -> bool:
        """Check if an executable or tool is present on the host system PATH."""
        return shutil.which(tool_name) is not None

    @staticmethod
    def run_command(
        cmd: List[str],
        cwd: Optional[str] = None,
        timeout: int = 10,
        env: Optional[Dict[str, str]] = None,
    ) -> Tuple_CommandResult:
        """Safely execute a CLI tool in an isolated subprocess with timeout."""
        try:
            res = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env or os.environ.copy(),
            )
            return Tuple_CommandResult(
                stdout=res.stdout,
                stderr=res.stderr,
                returncode=res.returncode,
                success=True,
                error=None,
            )
        except subprocess.TimeoutExpired:
            return Tuple_CommandResult(
                stdout="",
                stderr="Analysis process timed out.",
                returncode=124,
                success=False,
                error="TimeoutExpired",
            )
        except Exception as e:
            return Tuple_CommandResult(
                stdout="",
                stderr=str(e),
                returncode=-1,
                success=False,
                error=type(e).__name__,
            )

    @staticmethod
    def calculate_basic_metrics(code: str) -> Dict[str, Any]:
        """Compute lines of code, blank lines, comment lines, and basic complexity metrics."""
        lines = code.splitlines()
        loc = len(lines)
        blank = sum(1 for l in lines if not l.strip())
        comment = sum(
            1 for l in lines
            if l.strip().startswith(("#", "//", "/*", "*", "--", "<!--", ";", "%"))
        )
        code_lines = max(1, loc - blank - comment)
        return {
            "total_lines": loc,
            "code_lines": code_lines,
            "blank_lines": blank,
            "comment_lines": comment,
            "average_complexity": 1.0,
            "maintainability_index": round(max(0.0, min(100.0, 100.0 - (loc * 0.2))), 1),
        }


@dataclass
class Tuple_CommandResult:
    stdout: str
    stderr: str
    returncode: int
    success: bool
    error: Optional[str] = None
