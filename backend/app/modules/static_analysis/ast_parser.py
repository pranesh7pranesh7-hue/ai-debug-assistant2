"""AST Parser and Structural Code Inspector for Static Analysis."""
import ast
import builtins
from typing import Any, Dict, List, Set

BUILTINS = set(dir(builtins)) | {"__file__", "__name__", "__doc__", "__package__"}


class ASTInspector(ast.NodeVisitor):
    """Walks the Python AST to uncover structural flaws, bare exceptions, undefined variables, and resource hazards."""

    def __init__(self, code: str):
        self.code = code
        self.lines = code.splitlines()
        self.findings: List[Dict[str, Any]] = []

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        # Check for bare 'except:'
        if node.type is None:
            self.findings.append({
                "line": node.lineno,
                "column": node.col_offset,
                "tool": "ast",
                "rule_id": "AST-E001",
                "message": "Bare 'except:' clause catches SystemExit and KeyboardInterrupt. Specify Exception type.",
                "category": "error_handling",
            })
        elif isinstance(node.type, ast.Name) and node.type.id in ("BaseException", "Exception") and len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self.findings.append({
                "line": node.lineno,
                "column": node.col_offset,
                "tool": "ast",
                "rule_id": "AST-E002",
                "message": "Broad exception caught and silently ignored with 'pass'. This masks unexpected critical failures.",
                "category": "error_handling",
            })
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # Check for mutable default arguments
        for default in node.args.defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.findings.append({
                    "line": default.lineno,
                    "column": default.col_offset,
                    "tool": "ast",
                    "rule_id": "AST-W001",
                    "message": f"Dangerous mutable default argument ({type(default).__name__.lower()}) in function '{node.name}'. Use None as default instead.",
                    "category": "logic",
                })
        self.generic_visit(node)


def find_undefined_variables(tree: ast.AST) -> List[Dict[str, Any]]:
    """Inspect AST for module-level and function-level undefined variable references."""
    findings: List[Dict[str, Any]] = []
    defined_names: Set[str] = set()

    # 1. Collect all top-level defined names in module
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                defined_names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                defined_names.add(alias.asname or alias.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined_names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                for t in ast.walk(target):
                    if isinstance(t, ast.Name) and isinstance(t.ctx, ast.Store):
                        defined_names.add(t.id)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            if isinstance(node.target, ast.Name):
                defined_names.add(node.target.id)

    # 2. Check loaded names in each statement
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            local_defs: Set[str] = set(defined_names)
            for a in node.args.args:
                local_defs.add(a.arg)
            for a in getattr(node.args, "posonlyargs", []):
                local_defs.add(a.arg)
            for a in getattr(node.args, "kwonlyargs", []):
                local_defs.add(a.arg)
            if node.args.vararg:
                local_defs.add(node.args.vararg.arg)
            if node.args.kwarg:
                local_defs.add(node.args.kwarg.arg)

            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    for target in child.targets:
                        for t in ast.walk(target):
                            if isinstance(t, ast.Name) and isinstance(t.ctx, ast.Store):
                                local_defs.add(t.id)
                elif isinstance(child, (ast.AnnAssign, ast.AugAssign)) and isinstance(child.target, ast.Name):
                    local_defs.add(child.target.id)
                elif isinstance(child, ast.For):
                    for t in ast.walk(child.target):
                        if isinstance(t, ast.Name):
                            local_defs.add(t.id)
                elif isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                    if child.id not in local_defs and child.id not in BUILTINS:
                        findings.append({
                            "line": child.lineno,
                            "column": child.col_offset,
                            "tool": "ast",
                            "rule_id": "AST-E003",
                            "message": f"Undefined variable '{child.id}' referenced before assignment.",
                            "category": "logic",
                        })
        elif not isinstance(node, (ast.Import, ast.ImportFrom, ast.ClassDef)):
            for child in ast.walk(node):
                if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                    if child.id not in defined_names and child.id not in BUILTINS:
                        findings.append({
                            "line": child.lineno,
                            "column": child.col_offset,
                            "tool": "ast",
                            "rule_id": "AST-E003",
                            "message": f"Undefined variable '{child.id}' referenced before assignment.",
                            "category": "logic",
                        })

    return findings


def run_ast_analysis(code: str) -> List[Dict[str, Any]]:
    """Execute AST structural analysis on Python source code."""
    findings: List[Dict[str, Any]] = []
    try:
        tree = ast.parse(code)
        inspector = ASTInspector(code)
        inspector.visit(tree)
        findings.extend(inspector.findings)
        findings.extend(find_undefined_variables(tree))
    except SyntaxError as e:
        findings.append({
            "line": e.lineno or 1,
            "column": e.offset or 0,
            "tool": "ast",
            "rule_id": "AST-SYNTAX",
            "message": f"Syntax Error: {e.msg}",
            "category": "syntax",
        })
    return findings
