"""Tests for Language Selection Priority, ZIP Extraction, and Syntax Error Handling."""
import io
import zipfile
import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import CodeSyntaxError
from app.database import SessionLocal
from app.models.code_submission import CodeSubmission
from app.models.user import User
from app.modules.code_upload.uploader import CodeUploader
from app.modules.code_upload.validators import validate_code_syntax
from app.services.analysis_service import AnalysisService


@pytest.fixture
def db_session():
    db: Session = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def test_user(db_session: Session):
    user = db_session.query(User).filter(User.email == "lang_test_user@bugsense.ai").first()
    if not user:
        from app.core.security import get_password_hash
        user = User(
            email="lang_test_user@bugsense.ai",
            hashed_password=get_password_hash("password123"),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_python_selected_with_java_filename_no_false_positive_java_errors(db_session: Session, test_user: User):
    """Test 1: When user selects 'Python' from dropdown, even with a '.java' filename,
    the backend respects Python and does NOT run Java syntax checker (0 JAVA-SYNTAX errors).
    """
    python_code = """def calculate_average(numbers):
    if not numbers:
        return 0
    total = sum(numbers)
    return total / len(numbers)

print(calculate_average([10, 20, 30]))
"""
    # Explicitly submit with language="Python" despite filename="SyntaxErrorDemo.java"
    sub = CodeUploader.process_raw_code(
        db=db_session,
        user_id=test_user.id,
        raw_code=python_code,
        filename="SyntaxErrorDemo.java",
        language="Python",
    )

    assert sub.language == "Python"

    # Run full analysis
    analysis_res = await AnalysisService.run_full_analysis(db_session, sub.id)

    # Assert that no Java syntax rules or tools are reported
    bugs = analysis_res.get("bugs", [])
    java_syntax_bugs = [
        b for b in bugs
        if "JAVA-SYNTAX" in str(b.get("rule_id", ""))
        or "java_syntax_checker" in str(b.get("tool", ""))
        or "semicolon" in str(b.get("message", "")).lower()
    ]
    assert len(java_syntax_bugs) == 0, f"Expected 0 Java syntax errors, got: {java_syntax_bugs}"


@pytest.mark.asyncio
async def test_real_python_syntax_error_detected(db_session: Session, test_user: User):
    """Test 2: When real Python syntax error (e.g. missing colon) is analyzed with Python language,
    the Python syntax validator raises CodeSyntaxError.
    """
    broken_python = """def calculate_average(numbers)
    return sum(numbers) / len(numbers)
"""
    with pytest.raises(CodeSyntaxError) as exc_info:
        validate_code_syntax(broken_python, filename="calc.py", language="Python")

    err = exc_info.value
    assert err.code == "CODE_SYNTAX_ERROR"
    assert "line 1" in err.message.lower()


def test_zip_upload_extraction_populates_contents(db_session: Session, test_user: User):
    """Test 3: Uploading a .zip archive extracts files and populates raw_code."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("module_a.py", "def func_a():\n    return 42\n")
        zf.writestr("module_b.py", "def func_b():\n    return 'hello'\n")

    zip_bytes = zip_buffer.getvalue()

    subs = CodeUploader.process_file_upload(
        db=db_session,
        user_id=test_user.id,
        filename="test_project.zip",
        file_bytes=zip_bytes,
    )

    assert len(subs) == 2
    filenames = [s.filename for s in subs]
    assert "module_a.py" in filenames
    assert "module_b.py" in filenames

    for s in subs:
        assert s.raw_code is not None
        assert len(s.raw_code.strip()) > 0
        assert s.language == "Python"
