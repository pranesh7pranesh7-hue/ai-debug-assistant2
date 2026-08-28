"""BugSense AI Application Package."""

try:
    from app.main import app  # noqa: F401 – when cwd is backend/
except ImportError:
    from backend.app.main import app  # noqa: F401 – when cwd is project root
