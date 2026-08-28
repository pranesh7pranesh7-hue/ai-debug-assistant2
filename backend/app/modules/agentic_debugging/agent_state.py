"""Agentic Debugging State Definition."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class AgentAttempt:
    """Record of a single agentic attempt in the loop."""
    attempt_number: int
    action: str  # plan, act, observe, verify, retry
    diff: Optional[str] = None
    observation: str = ""
    is_verified: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AgentState:
    """Current state of the agentic debugging session."""
    submission_id: int
    filename: str
    original_code: str
    current_code: str
    target_bugs: List[Dict[str, Any]]
    language: str = "Python"
    active_bug_index: int = 0
    attempt_count: int = 0
    max_retries: int = 3
    is_completed: bool = False
    is_verified: bool = False
    test_code: Optional[str] = None
    history: List[AgentAttempt] = field(default_factory=list)

    def current_bug(self) -> Optional[Dict[str, Any]]:
        if 0 <= self.active_bug_index < len(self.target_bugs):
            return self.target_bugs[self.active_bug_index]
        return None
