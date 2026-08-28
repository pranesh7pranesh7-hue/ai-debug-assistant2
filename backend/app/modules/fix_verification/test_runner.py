"""Test Runner Module.
Executes pytest against patched code in the sandbox.
"""
from typing import Optional, Tuple
from app.modules.agentic_debugging.sandbox_executor import SandboxExecutor


class TestRunner:
    """Runs automated test suites against patched code."""

    @staticmethod
    def run_tests(patched_code: str, test_code: Optional[str] = None) -> Tuple[bool, str]:
        """Execute tests against patched code and return (passed: bool, output_logs: str)."""
        if not test_code:
            # Without explicit test suite, check if the code runs without top-level crash
            success, code, stdout, stderr = SandboxExecutor.execute_in_sandbox(patched_code)
            logs = f"Execution Code: {code}\nSTDOUT: {stdout}\nSTDERR: {stderr}"
            return success, logs

        success, code, stdout, stderr = SandboxExecutor.execute_in_sandbox(
            code=patched_code,
            test_code=test_code,
        )
        logs = f"Pytest Exit Code: {code}\n{stdout}\n{stderr}"
        return success, logs
