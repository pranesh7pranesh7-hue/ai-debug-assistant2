"""Retry Policy and Decision Engine for Agentic Loop."""
from typing import Optional, Tuple

from app.modules.agentic_debugging.agent_state import AgentState


class RetryPolicy:
    """Decides whether to retry an agentic fix attempt and constructs refined guidance."""

    @staticmethod
    def should_retry(state: AgentState) -> Tuple[bool, Optional[str]]:
        """Evaluate if another attempt should be executed based on state history and retry counts."""
        if state.attempt_count >= state.max_retries:
            return False, f"Exhausted maximum configured retry attempts ({state.max_retries})."

        last_attempt = state.history[-1] if state.history else None
        if not last_attempt:
            return True, None

        if last_attempt.is_verified:
            return False, "Fix successfully verified. No retry needed."

        # Formulate feedback instruction from observation
        feedback = f"Previous patch failed verification with observation: {last_attempt.observation}. Please refine patch to fix the issue without introducing errors."
        return True, feedback
