"""Tests for Static Analysis Module."""
import pytest
from app.modules.static_analysis.ast_parser import run_ast_analysis
from app.modules.static_analysis.aggregator import run_all_static_analyzers


def test_ast_parser_detects_mutable_default():
    code = "def bad_func(a, b=[]):\n    b.append(a)\n    return b"
    findings = run_ast_analysis(code)
    assert any(f["rule_id"] == "AST-W001" for f in findings)


def test_ast_parser_detects_bare_except():
    code = "try:\n    x = 1\nexcept:\n    pass"
    findings = run_ast_analysis(code)
    assert any(f["rule_id"] == "AST-E001" for f in findings)


@pytest.mark.asyncio
async def test_aggregator_unifies_schema():
    code = "def sample(x, items=[]):\n    f = open('test.txt')\n    return items"
    findings, metrics = await run_all_static_analyzers(code)
    assert isinstance(findings, list)
    assert isinstance(metrics, dict)
    for f in findings:
        assert "line" in f
        assert "column" in f
        assert "tool" in f
        assert "rule_id" in f
        assert "message" in f
        assert "category" in f
