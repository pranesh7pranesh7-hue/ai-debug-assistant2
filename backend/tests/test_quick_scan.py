"""Tests for Quick Scan functionality, code normalization, and syntax error envelopes."""
import pytest
from app.core.exceptions import CodeSyntaxError, ValidationError
from app.modules.bug_detection.detector import detect_all_bugs
from app.modules.code_upload.validators import (
    normalize_python_code,
    validate_python_code,
)


def test_quick_scan_test1_valid_python():
    """Test 1: Valid Python function definition and call."""
    code = """def greet(name):
    return f"Hello, {name}"

print(greet("World"))"""
    valid, msg = validate_python_code(code)
    assert valid is True
    assert "Valid Python syntax" in msg


def test_quick_scan_test2_class_example():
    """Test 2: Class definition and initialization (must not produce false syntax error)."""
    code = """class Person:
    def __init__(self, name):
        self.name = name

person = Person("John")
print(person.name)
print("Program finished")"""
    valid, msg = validate_python_code(code)
    assert valid is True
    assert "Valid Python syntax" in msg


def test_quick_scan_test3_intentional_syntax_error():
    """Test 3: Intentional syntax error (missing colon) raises structured CodeSyntaxError."""
    code = """def greet(name)
    print(name)"""
    with pytest.raises(CodeSyntaxError) as exc_info:
        validate_python_code(code)
    
    err = exc_info.value
    assert err.code == "CODE_SYNTAX_ERROR"
    assert err.status_code == 422
    assert "line 1" in err.message.lower()
    assert err.details.get("line") == 1
    assert "column" in err.details


def test_quick_scan_test4_buggy_but_syntactically_valid():
    """Test 4: Buggy code (division by zero) is syntactically valid and caught by bug detector."""
    code = """def divide(a, b):
    return a / b

result = divide(10, 0)
print(result)"""
    # 1. Must pass syntax check
    valid, msg = validate_python_code(code)
    assert valid is True

    # 2. Bug detector should identify the division by zero hazard
    import asyncio
    findings, metrics = asyncio.run(detect_all_bugs(code))
    div_zero_bugs = [f for f in findings if "zerodivision" in f["message"].lower() or f["rule_id"] == "BUG-PAT-008"]
    assert len(div_zero_bugs) > 0


def test_quick_scan_test5_empty_input():
    """Test 5: Empty or whitespace-only code raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        validate_python_code("")
    assert "cannot be empty" in exc_info.value.message

    with pytest.raises(ValidationError) as exc_info:
        validate_python_code("   \n\t   \n  ")
    assert "cannot be empty" in exc_info.value.message


def test_quick_scan_markdown_fence_normalization():
    """Test that Markdown-fenced code is safely stripped and parsed."""
    fenced_code = """```python
class Person:
    def __init__(self, name):
        self.name = name

person = Person("John")
print(person.name)
print("Program finished")
```"""
    normalized = normalize_python_code(fenced_code)
    assert not normalized.startswith("```")
    assert not normalized.endswith("```")
    assert "class Person:" in normalized
    valid, msg = validate_python_code(fenced_code)
    assert valid is True


def test_quick_scan_line_number_prefix_normalization():
    """Test that code copied with line numbers (e.g. 44  class Person:) is normalized and parsed."""
    numbered_code = """44  class Person:
45      def __init__(self, name):
46          self.name = name
47  
48  person = Person("John")
49  print(person.name)
50  print("Program finished")"""
    normalized = normalize_python_code(numbered_code)
    assert "44 " not in normalized
    assert "class Person:" in normalized
    valid, msg = validate_python_code(numbered_code)
    assert valid is True
