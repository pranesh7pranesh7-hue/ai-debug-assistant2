"""BugSense Custom Exception Hierarchy.
All application exceptions derive from BugSenseException for structured JSON error envelopes.
"""
from typing import Any, Dict, Optional


class BugSenseException(Exception):
    """Base exception for all BugSense application errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class ValidationError(BugSenseException):
    """Raised when code validation or input data format checks fail."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=400,
            details=details,
        )


class CodeSyntaxError(BugSenseException):
    """Raised when Python code fails AST parsing or syntax verification."""

    def __init__(self, message: str, line: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        d = details or {}
        if line is not None:
            d["line"] = line
        super().__init__(
            message=message,
            code="CODE_SYNTAX_ERROR",
            status_code=422,
            details=d,
        )


class AnalysisError(BugSenseException):
    """Raised when a static analysis tool encounters a failure during execution."""

    def __init__(self, message: str, tool: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        d = details or {}
        if tool:
            d["tool"] = tool
        super().__init__(
            message=message,
            code="ANALYSIS_ERROR",
            status_code=500,
            details=d,
        )


class LLMProviderError(BugSenseException):
    """Raised when LLM API call fails, encounters rate limiting, or returns malformed response."""

    def __init__(self, message: str, provider: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        d = details or {}
        if provider:
            d["provider"] = provider
        super().__init__(
            message=message,
            code="LLM_PROVIDER_ERROR",
            status_code=502,
            details=d,
        )


class SandboxExecutionError(BugSenseException):
    """Raised when sandbox execution violates resource limits, times out, or fails security checks."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="SANDBOX_EXECUTION_ERROR",
            status_code=408,
            details=details,
        )


class AuthError(BugSenseException):
    """Raised when JWT validation, authentication, or permission check fails."""

    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="AUTH_ERROR",
            status_code=401,
            details=details,
        )


class NotFoundError(BugSenseException):
    """Raised when a requested resource (submission, bug, report) is not found."""

    def __init__(self, resource: str, resource_id: Any):
        super().__init__(
            message=f"{resource} with identifier '{resource_id}' not found.",
            code="NOT_FOUND",
            status_code=404,
            details={"resource": resource, "id": str(resource_id)},
        )
