"""Agentic Debugging Service.
Starts and monitors autonomous agentic repair sessions.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.agentic_run import AgenticRun
from app.models.bug import Bug
from app.models.code_submission import CodeSubmission
from app.modules.agentic_debugging.agent_orchestrator import AgentOrchestrator
from app.modules.agentic_debugging.agent_state import AgentState

logger = logging.getLogger("bugsense.agentic_service")

# In-memory tracking of running sessions
_active_agent_sessions: Dict[int, Dict[str, Any]] = {}


class AgenticService:
    """Coordinates agentic loop execution and status queries."""

    @staticmethod
    async def start_agentic_loop(
        db: Session,
        submission_id: int,
        bug_ids: Optional[List[int]] = None,
        max_retries: int = 3,
        test_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Initialize and execute agentic loop."""
        sub = db.query(CodeSubmission).filter(CodeSubmission.id == submission_id).first()
        if not sub:
            raise NotFoundError("CodeSubmission", submission_id)

        # Query target bugs
        bug_query = db.query(Bug).filter(Bug.submission_id == submission_id)
        if bug_ids:
            bug_query = bug_query.filter(Bug.id.in_(bug_ids))
        bugs = bug_query.all()

        if not bugs:
            # Re-run static analysis first if no bugs recorded
            from app.services.analysis_service import AnalysisService
            res = await AnalysisService.run_full_analysis(db, submission_id)
            bugs = db.query(Bug).filter(Bug.submission_id == submission_id).all()

        target_bug_dicts = [
            {
                "id": b.id,
                "line": b.line,
                "column": b.column,
                "tool": b.tool,
                "rule_id": b.rule_id,
                "category": b.category,
                "message": b.message,
                "severity": b.severity,
                "explanation": b.explanation or "",
            }
            for b in bugs
        ]

        state = AgentState(
            submission_id=sub.id,
            filename=sub.filename,
            original_code=sub.raw_code,
            current_code=sub.raw_code,
            target_bugs=target_bug_dicts,
            language=sub.language or "Python",
            max_retries=max_retries,
            test_code=test_code,
        )

        orchestrator = AgentOrchestrator(db, state)

        _active_agent_sessions[submission_id] = {
            "is_running": True,
            "state": state,
        }

        # Run loop
        final_state = await orchestrator.run_loop()

        _active_agent_sessions[submission_id]["is_running"] = False
        _active_agent_sessions[submission_id]["final_code"] = final_state.current_code

        return {
            "submission_id": submission_id,
            "status": "completed" if final_state.is_completed else "failed",
            "is_verified": final_state.is_verified,
            "total_attempts": len(final_state.history),
            "final_code": final_state.current_code,
        }

    @staticmethod
    def get_agentic_status(db: Session, submission_id: int) -> Dict[str, Any]:
        """Fetch live or completed agentic status and history logs."""
        sub = db.query(CodeSubmission).filter(CodeSubmission.id == submission_id).first()
        if not sub:
            raise NotFoundError("CodeSubmission", submission_id)

        runs = (
            db.query(AgenticRun)
            .filter(AgenticRun.submission_id == submission_id)
            .order_by(AgenticRun.id.asc())
            .all()
        )

        is_running = False
        final_code = sub.raw_code
        if submission_id in _active_agent_sessions:
            is_running = _active_agent_sessions[submission_id].get("is_running", False)
            final_code = _active_agent_sessions[submission_id].get("final_code", sub.raw_code)

        verified_runs = [r for r in runs if r.verified]
        total_bugs = db.query(Bug).filter(Bug.submission_id == submission_id).count()

        return {
            "submission_id": submission_id,
            "status": "verified" if verified_runs else ("in_progress" if is_running else "completed"),
            "total_bugs": total_bugs,
            "fixed_bugs": len(verified_runs),
            "current_attempt": len(runs),
            "max_retries": 3,
            "is_running": is_running,
            "final_code": final_code,
            "logs": [
                {
                    "attempt_number": r.attempt_number,
                    "action_taken": r.action_taken,
                    "diff_applied": r.diff_applied,
                    "outcome": r.outcome,
                    "verified": r.verified,
                    "created_at": r.created_at,
                }
                for r in runs
            ],
        }
