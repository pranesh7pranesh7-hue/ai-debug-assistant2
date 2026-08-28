"""Tests for Fix Recommendation, Language-Aware Patch Synthesis, and Unified Diff Application."""
import pytest
from app.modules.fix_recommendation.diff_generator import (
    apply_unified_diff,
    create_unified_diff,
    get_comment_prefix,
    validate_and_apply_patch,
)
from app.modules.fix_recommendation.recommender import (
    FixRecommender,
    synthesize_deterministic_fix,
)


def test_create_unified_diff():
    original = "def add(a, b=[]):\n    return a"
    patched = "def add(a, b=None):\n    if b is None:\n        b = []\n    return a"
    diff = create_unified_diff(original, patched, filename="math_utils.py")
    assert "--- a/math_utils.py" in diff
    assert "+++ b/math_utils.py" in diff
    assert "-def add(a, b=[]):" in diff
    assert "+def add(a, b=None):" in diff


def test_validate_and_apply_patch_valid():
    original = "x = 1"
    patched = "x = 2"
    valid, diff, err = validate_and_apply_patch(original, patched)
    assert valid is True
    assert err is None
    assert diff is not None


def test_validate_and_apply_patch_syntax_error():
    original = "x = 1"
    patched = "x = (invalid syntax"
    valid, diff, err = validate_and_apply_patch(original, patched, language="Python")
    assert valid is False
    assert "syntax error" in err.lower()


@pytest.mark.asyncio
async def test_deterministic_fix_for_mutable_default():
    code = "def append_item(x, items=[]):\n    items.append(x)\n    return items"
    patched, rationale = synthesize_deterministic_fix(code, 1, "logic", "mutable default argument", language="Python")
    assert patched is not None
    assert "items=None" in patched
    assert "mutable default" in rationale.lower()


@pytest.mark.asyncio
async def test_java_missing_semicolon_real_fix_and_appliable_diff():
    """Test 1: Missing semicolon in Java outputs real corrected line (with ';'), not a placeholder comment.
    Diff applies cleanly and rationale describes the real change.
    """
    java_code = """public class SyntaxErrorDemo {
    public static void main(String[] args) {
        int number = 10
        System.out.println("Number: " + number);
    }
}
"""
    # Line 3 is '        int number = 10'
    patched, rationale = synthesize_deterministic_fix(
        raw_code=java_code,
        line=3,
        category="syntax",
        message="Syntax Error: Missing semicolon ';' at end of statement.",
        rule_id="JAVA-SYNTAX-SEMICOLON",
        language="Java",
    )

    assert patched is not None
    assert "int number = 10;" in patched
    assert "# TODO" not in patched
    assert "// TODO" not in patched
    assert "semicolon" in rationale.lower()

    # Generate unified diff and verify clean application
    valid, diff_text, err = validate_and_apply_patch(
        original_code=java_code,
        patched_code=patched,
        language="Java",
        filename="SyntaxErrorDemo.java",
    )
    assert valid is True
    assert err is None
    assert "-        int number = 10\n" in diff_text
    assert "+        int number = 10;\n" in diff_text
    assert "--- a/SyntaxErrorDemo.java" in diff_text
    assert "+++ b/SyntaxErrorDemo.java" in diff_text

    # Apply diff directly to verify hunk accuracy
    success, applied_code, app_err = apply_unified_diff(java_code, diff_text)
    assert success is True
    assert app_err is None
    assert applied_code.strip() == patched.strip()


@pytest.mark.asyncio
async def test_python_missing_colon_real_fix_and_appliable_diff():
    """Test 2: Missing colon in Python header (if/def) outputs real fix with ':',
    diff applies cleanly, and rationale describes the change.
    """
    python_code = """def calculate_average(numbers)
    if not numbers
        return 0
    return sum(numbers) / len(numbers)
"""
    # Fix missing colon on def line
    patched_def, rationale_def = synthesize_deterministic_fix(
        raw_code=python_code,
        line=1,
        category="syntax",
        message="Python syntax error: expected ':'",
        rule_id="PY-SYNTAX-001",
        language="Python",
    )

    assert patched_def is not None
    assert "def calculate_average(numbers):" in patched_def
    assert "colon" in rationale_def.lower()

    valid, diff_def, err = validate_and_apply_patch(
        original_code=python_code,
        patched_code=patched_def,
        language="Python",
        filename="calc.py",
    )
    assert valid is True
    assert err is None
    assert "-def calculate_average(numbers)\n" in diff_def
    assert "+def calculate_average(numbers):\n" in diff_def

    # Test applying diff
    success, applied, app_err = apply_unified_diff(python_code, diff_def)
    assert success is True
    assert applied.strip() == patched_def.strip()

    # Fix missing colon on if line
    patched_if, rationale_if = synthesize_deterministic_fix(
        raw_code=patched_def,
        line=2,
        category="syntax",
        message="Python syntax error: expected ':'",
        rule_id="PY-SYNTAX-001",
        language="Python",
    )
    assert patched_if is not None
    assert "if not numbers:" in patched_if
    assert "colon" in rationale_if.lower()


def test_comment_prefix_respects_target_language():
    """Test 3: get_comment_prefix returns correct syntax per language."""
    assert get_comment_prefix("Java") == "//"
    assert get_comment_prefix("C") == "//"
    assert get_comment_prefix("C++") == "//"
    assert get_comment_prefix("JavaScript") == "//"
    assert get_comment_prefix("TypeScript") == "//"
    assert get_comment_prefix("Go") == "//"
    assert get_comment_prefix("Rust") == "//"
    assert get_comment_prefix("C#") == "//"
    assert get_comment_prefix("PHP") == "//"
    assert get_comment_prefix("Python") == "#"
    assert get_comment_prefix("Ruby") == "#"
    assert get_comment_prefix("Shell") == "#"
    assert get_comment_prefix("SQL") == "--"


@pytest.mark.asyncio
async def test_fix_recommender_generate_fix_java_semicolon():
    """Test 4: Full FixRecommender.generate_fix with Java missing semicolon returns valid diff."""
    java_code = "class A {\n    int x = 5\n}"
    res = await FixRecommender.generate_fix(
        raw_code=java_code,
        line=2,
        tool="java_syntax_checker",
        rule_id="JAVA-SYNTAX-SEMICOLON",
        message="Syntax Error: Missing semicolon ';' at end of statement.",
        category="syntax",
        explanation="Statements in Java must terminate with a semicolon ';'.",
        language="Java",
        filename="A.java",
    )

    assert res["status"] == "proposed"
    assert "int x = 5;" in res["patched_code"]
    assert "-    int x = 5\n" in res["diff_text"]
    assert "+    int x = 5;\n" in res["diff_text"]
    assert "semicolon" in res["rationale"].lower()

