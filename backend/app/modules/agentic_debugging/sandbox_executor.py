"""Sandbox Executor Module.
Executes Python code and test suites safely in an isolated temporary directory with timeout and environment restrictions.
"""
import os
import subprocess
import sys
import tempfile
from typing import Dict, Optional, Tuple

from app.config import get_settings
from app.core.exceptions import SandboxExecutionError


class SandboxExecutor:
    """Safe isolated runner for Python code and test executions."""

    @staticmethod
    def execute_in_sandbox(
        code: str,
        test_code: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ) -> Tuple[bool, int, str, str]:
        """Runs the code (and optional test code) inside an isolated subprocess.
        Returns: (success: bool, returncode: int, stdout: str, stderr: str)
        """
        settings = get_settings()
        timeout = timeout_seconds or settings.SANDBOX_TIMEOUT_SECONDS

        with tempfile.TemporaryDirectory() as sandbox_dir:
            # 1. Write target code file
            code_path = os.path.join(sandbox_dir, "solution.py")
            with open(code_path, "w", encoding="utf-8") as f:
                f.write(code)

            # 2. If test code provided, write test file
            target_cmd = [sys.executable, code_path]
            if test_code:
                test_path = os.path.join(sandbox_dir, "test_solution.py")
                with open(test_path, "w", encoding="utf-8") as f:
                    # Prepend import solution if not already importing
                    content = test_code
                    if "import solution" not in content and "from solution" not in content:
                        content = "import solution\n" + content
                    f.write(content)
                target_cmd = [sys.executable, "-m", "pytest", test_path, "-q"]

            # 3. Sanitize Environment (Strip sensitive keys)
            clean_env: Dict[str, str] = {
                "PYTHONPATH": sandbox_dir,
                "PYTHONIOENCODING": "utf-8",
                "PATH": os.environ.get("PATH", ""),
                "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
            }

            try:
                proc = subprocess.run(
                    target_cmd,
                    cwd=sandbox_dir,
                    env=clean_env,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                success = (proc.returncode == 0)
                return success, proc.returncode, proc.stdout, proc.stderr

            except subprocess.TimeoutExpired as te:
                stdout = te.stdout or ""
                stderr = te.stderr or f"Execution timed out after {timeout} seconds."
                return False, -1, stdout, stderr

            except Exception as e:
                return False, -2, "", f"Sandbox initialization error: {str(e)}"
