from app.modules.agentic_debugging.sandbox_executor import SandboxExecutor
from app.modules.agentic_debugging.retry_policy import RetryPolicy
from app.modules.agentic_debugging.agent_state import AgentState


def test_sandbox_executes_safely():
    safe_code = "print('Hello BugSense')"
    success, retcode, stdout, stderr = SandboxExecutor.execute_in_sandbox(safe_code)
    assert success is True
    assert retcode == 0
    assert "Hello BugSense" in stdout


def test_sandbox_handles_runtime_error():
    crash_code = "1 / 0"
    success, retcode, stdout, stderr = SandboxExecutor.execute_in_sandbox(crash_code)
    assert success is False
    assert retcode != 0
    assert "ZeroDivisionError" in stderr


def test_retry_policy_limits():
    state = AgentState(
        submission_id=1,
        filename="test.py",
        original_code="pass",
        current_code="pass",
        target_bugs=[],
        attempt_count=3,
        max_retries=3,
    )
    should_retry, _ = RetryPolicy.should_retry(state)
    assert should_retry is False
