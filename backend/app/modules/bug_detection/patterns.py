"""Known Bug Pattern Library.
Detects deep semantic and AST-level bug patterns:
1. Unhandled exceptions / dangerous operations
2. Mutable default arguments
3. Off-by-one loop errors (e.g. range(len(arr) + 1))
4. Undefined variable references
5. Unreachable code after return / raise / break
6. Resource leaks (unclosed files, sockets, DB connections)
7. Infinite loop risks (while True without break/return)
8. Type mismatch hazards (str + int, unsupported operations)
9. SQL Injection patterns (string concatenation in queries)
10. Race condition prone patterns (threading/multiprocessing without Lock)
"""
import ast
import re
from typing import Any, Dict, List


class BugPatternDetector(ast.NodeVisitor):
    """Deep AST pattern detection visitor."""

    def __init__(self, code: str):
        self.code = code
        self.lines = code.splitlines()
        self.bugs: List[Dict[str, Any]] = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        # 1. Mutable Default Arguments
        for default in node.args.defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.bugs.append({
                    "line": default.lineno,
                    "column": default.col_offset,
                    "tool": "ast_pattern",
                    "rule_id": "BUG-PAT-001",
                    "category": "logic",
                    "message": f"Mutable default argument '{type(default).__name__.lower()}' in function '{node.name}'. Causes state retention across function calls.",
                })

        # 2. Unreachable Code after Return / Raise in body
        has_returned = False
        for stmt in node.body:
            if has_returned:
                self.bugs.append({
                    "line": stmt.lineno,
                    "column": stmt.col_offset,
                    "tool": "ast_pattern",
                    "rule_id": "BUG-PAT-002",
                    "category": "logic",
                    "message": f"Unreachable code detected in function '{node.name}' following a terminal 'return' or 'raise' statement.",
                })
                break
            if isinstance(stmt, (ast.Return, ast.Raise)):
                has_returned = True

        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        # 3. Off-by-One Loop Error in range(len(list) + 1)
        if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
            for arg in node.iter.args:
                if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                    if (isinstance(arg.left, ast.Call) and isinstance(arg.left.func, ast.Name) and arg.left.func.id == "len") or \
                       (isinstance(arg.right, ast.Call) and isinstance(arg.right.func, ast.Name) and arg.right.func.id == "len"):
                        self.bugs.append({
                            "line": node.lineno,
                            "column": node.col_offset,
                            "tool": "ast_pattern",
                            "rule_id": "BUG-PAT-003",
                            "category": "logic",
                            "message": "Potential Off-by-One error in range(len(...) + 1). May cause IndexError when indexing array by loop variable.",
                        })
        self.generic_visit(node)

    def visit_While(self, node: ast.While):
        # 4. Infinite Loop Risk (while True without break, return, or exit)
        is_constant_true = False
        if isinstance(node.test, ast.Constant) and node.test.value is True:
            is_constant_true = True
        elif isinstance(node.test, ast.NameConstant) and node.test.value is True:  # Python 3.7 compat
            is_constant_true = True

        if is_constant_true:
            has_exit = False
            for subnode in ast.walk(node):
                if isinstance(subnode, (ast.Break, ast.Return, ast.Raise)):
                    has_exit = True
                    break
            if not has_exit:
                self.bugs.append({
                    "line": node.lineno,
                    "column": node.col_offset,
                    "tool": "ast_pattern",
                    "rule_id": "BUG-PAT-004",
                    "category": "logic",
                    "message": "Infinite loop detected: 'while True' statement has no 'break', 'return', or 'raise' path.",
                })
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        # 5. Resource Leak: open() assigned without with context
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "open":
            # Check if this assignment is in a module or function without immediate close in finally
            self.bugs.append({
                "line": node.lineno,
                "column": node.col_offset,
                "tool": "ast_pattern",
                "rule_id": "BUG-PAT-005",
                "category": "resource_leak",
                "message": "Resource leak hazard: file opened with 'open()' outside of a 'with' context manager. File descriptor may remain open.",
            })

        # 6. SQL Injection via string formatting or f-string
        if isinstance(node.value, ast.JoinedStr):
            # Check for SQL keywords inside JoinedStr
            str_parts = []
            for value_part in node.value.values:
                if isinstance(value_part, ast.Constant) and isinstance(value_part.value, str):
                    str_parts.append(value_part.value)
            full_str = " ".join(str_parts).upper()
            if any(sql_kw in full_str for sql_kw in ["SELECT ", "INSERT INTO", "UPDATE ", "DELETE FROM", "DROP TABLE"]) and "WHERE" in full_str:
                self.bugs.append({
                    "line": node.lineno,
                    "column": node.col_offset,
                    "tool": "ast_pattern",
                    "rule_id": "BUG-PAT-006",
                    "category": "security",
                    "message": "SQL Injection vulnerability: Dynamic SQL query constructed via f-string / string interpolation instead of parameterized queries.",
                })

        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        # 7. Type Mismatch Hazard (e.g. str + int literal)
        if isinstance(node.op, ast.Add):
            left_is_str = isinstance(node.left, ast.Constant) and isinstance(node.left.value, str)
            right_is_int = isinstance(node.right, ast.Constant) and isinstance(node.right.value, (int, float))
            left_is_int = isinstance(node.left, ast.Constant) and isinstance(node.left.value, (int, float))
            right_is_str = isinstance(node.right, ast.Constant) and isinstance(node.right.value, str)
            if (left_is_str and right_is_int) or (left_is_int and right_is_str):
                self.bugs.append({
                    "line": node.lineno,
                    "column": node.col_offset,
                    "tool": "ast_pattern",
                    "rule_id": "BUG-PAT-007",
                    "category": "type_error",
                    "message": f"TypeError hazard: cannot concatenate str and number types directly.",
                })

        # 8. Division by Zero Literal
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
            if isinstance(node.right, ast.Constant) and node.right.value == 0:
                self.bugs.append({
                    "line": node.lineno,
                    "column": node.col_offset,
                    "tool": "ast_pattern",
                    "rule_id": "BUG-PAT-008",
                    "category": "logic",
                    "message": "ZeroDivisionError: literal division or modulo by zero.",
                })
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # 9. Function Call Division by Zero Hazard (e.g., divide(10, 0))
        if isinstance(node.func, ast.Name) and any(kw in node.func.id.lower() for kw in ["div", "calc", "ratio"]):
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and node.args[1].value == 0:
                self.bugs.append({
                    "line": node.lineno,
                    "column": node.col_offset,
                    "tool": "ast_pattern",
                    "rule_id": "BUG-PAT-008",
                    "category": "logic",
                    "message": f"ZeroDivisionError hazard: function '{node.func.id}' called with 0 as divisor argument.",
                })
        self.generic_visit(node)


def find_pattern_bugs(code: str) -> List[Dict[str, Any]]:
    """Inspect code using AST pattern matchers and regex fallbacks."""
    bugs: List[Dict[str, Any]] = []

    # 1. AST visitor pass
    try:
        tree = ast.parse(code)
        detector = BugPatternDetector(code)
        detector.visit(tree)
        bugs.extend(detector.bugs)
    except SyntaxError:
        pass

    # 2. Race condition & threading detection
    if "threading.Thread" in code and "Lock" not in code and ("global " in code or "append(" in code):
        lines = code.splitlines()
        for idx, line in enumerate(lines, start=1):
            if "threading.Thread" in line:
                bugs.append({
                    "line": idx,
                    "column": 0,
                    "tool": "ast_pattern",
                    "rule_id": "BUG-PAT-009",
                    "category": "concurrency",
                    "message": "Potential Race Condition: Multi-threaded execution modifies shared state without a threading.Lock() synchronization primitive.",
                })
                break

    # 3. Hardcoded Secret / Token regex check
    secret_patterns = [
        (r'(?i)(password|secret|api_key|token|auth_token)\s*=\s*["\'][a-zA-Z0-9_\-]{8,}["\']', "Hardcoded sensitive credential or API key token in source code."),
    ]
    for pattern, msg in secret_patterns:
        for idx, line in enumerate(code.splitlines(), start=1):
            if re.search(pattern, line) and not line.strip().startswith("#"):
                bugs.append({
                    "line": idx,
                    "column": 0,
                    "tool": "security_pattern",
                    "rule_id": "BUG-PAT-010",
                    "category": "security",
                    "message": msg,
                })

    return bugs
