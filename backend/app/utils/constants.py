"""System-wide constants, severity tiers, and categories for BugSense AI."""

# Severity Tiers
SEVERITY_CRITICAL = "Critical"
SEVERITY_HIGH = "High"
SEVERITY_MEDIUM = "Medium"
SEVERITY_LOW = "Low"
SEVERITY_INFO = "Info"

SEVERITY_LEVELS = [
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_LOW,
    SEVERITY_INFO,
]

# Bug Categories
CATEGORY_SECURITY = "security"
CATEGORY_SYNTAX = "syntax"
CATEGORY_LOGIC = "logic"
CATEGORY_RESOURCE_LEAK = "resource_leak"
CATEGORY_PERFORMANCE = "performance"
CATEGORY_STYLE = "style"
CATEGORY_COMPLEXITY = "complexity"
CATEGORY_ERROR_HANDLING = "error_handling"
CATEGORY_TYPE_ERROR = "type_error"
CATEGORY_CONCURRENCY = "concurrency"

# Fix Statuses
FIX_STATUS_PROPOSED = "proposed"
FIX_STATUS_APPLIED = "applied"
FIX_STATUS_VERIFIED = "verified"
FIX_STATUS_REJECTED = "rejected"
FIX_STATUS_FAILED = "failed"

# Agentic Run Actions
ACTION_PLAN = "plan"
ACTION_ACT = "act"
ACTION_OBSERVE = "observe"
ACTION_VERIFY = "verify"
ACTION_RETRY = "retry"
