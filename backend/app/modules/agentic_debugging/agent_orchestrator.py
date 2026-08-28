"""Agentic Debugging Orchestrator.
Manual state machine implementing the Plan -> Act -> Observe -> Verify -> Retry loop.
"""
import logging
from typing import Any, Callable, Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.agentic_run import AgenticRun
from app.models.bug import Bug
from app.models.fix import Fix
from app.modules.agentic_debugging.agent_state import AgentAttempt, AgentState
from app.modules.agentic_debugging.retry_policy import RetryPolicy
from app.modules.agentic_debugging.sandbox_executor import SandboxExecutor
from app.modules.fix_recommendation.diff_generator import create_unified_diff, validate_and_apply_patch
from app.modules.fix_recommendation.recommender import FixRecommender
from app.modules.fix_verification.verifier import FixVerifier

logger = logging.getLogger("bugsense.agentic")


class AgentOrchestrator:
    """Coordinates autonomous debugging loop for code submissions."""

    def __init__(self, db: Session, state: AgentState):
        self.db = db
        self.state = state

    async def run_loop(self, step_callback: Optional[Callable[[AgentAttempt], None]] = None) -> AgentState:
        """Execute the full autonomous agentic loop until all target bugs are fixed or retries exhausted."""
        logger.info("Starting Agentic Loop for submission %s with %d target bugs", self.state.submission_id, len(self.state.target_bugs))

        for bug_idx, bug_info in enumerate(self.state.target_bugs):
            self.state.active_bug_index = bug_idx
            self.state.attempt_count = 0
            bug_db_id = bug_info.get("id")

            while True:
                self.state.attempt_count += 1
                attempt_num = self.state.attempt_count

                # 1. PLAN PHASE
                # -----------------------------------------------
                plan_log = self._record_step(
                    bug_id=bug_db_id,
                    attempt=attempt_num,
                    action="plan",
                    outcome=f"Formulating fix strategy for {bug_info.get('rule_id')} on line {bug_info.get('line')}",
                )
                if step_callback:
                    step_callback(plan_log)

                # 2. ACT PHASE (Synthesize patch)
                # -----------------------------------------------
                fix_data = await FixRecommender.generate_fix(
                    raw_code=self.state.current_code,
                    line=bug_info.get("line", 1),
                    tool=bug_info.get("tool", "ast"),
                    rule_id=bug_info.get("rule_id", "GENERIC"),
                    message=bug_info.get("message", ""),
                    category=bug_info.get("category", "logic"),
                    explanation=bug_info.get("explanation", ""),
                    custom_instruction=getattr(self.state, "custom_feedback", ""),
                    language=self.state.language,
                    filename=self.state.filename,
                )

                patched_candidate = fix_data.get("patched_code", self.state.current_code)
                diff_applied = fix_data.get("diff_text", "")

                act_log = self._record_step(
                    bug_id=bug_db_id,
                    attempt=attempt_num,
                    action="act",
                    diff=diff_applied,
                    outcome=f"Synthesized patch with rationale: {fix_data.get('rationale')}",
                )
                if step_callback:
                    step_callback(act_log)

                # 3. OBSERVE PHASE (Execute in sandbox)
                # -----------------------------------------------
                exec_ok, retcode, stdout, stderr = SandboxExecutor.execute_in_sandbox(
                    code=patched_candidate,
                    test_code=self.state.test_code,
                )

                obs_text = f"Exit code {retcode}. Output: {stdout.strip()[:200]}"
                if stderr.strip():
                    obs_text += f" | Errors: {stderr.strip()[:200]}"

                observe_log = self._record_step(
                    bug_id=bug_db_id,
                    attempt=attempt_num,
                    action="observe",
                    diff=diff_applied,
                    outcome=obs_text,
                )
                if step_callback:
                    step_callback(observe_log)

                # 4. VERIFY PHASE
                # -----------------------------------------------
                verification_result = await FixVerifier.verify_patch(
                    original_code=self.state.current_code,
                    patched_code=patched_candidate,
                    target_bug=bug_info,
                    sandbox_success=exec_ok,
                )

                is_verified = verification_result.get("passed", False)
                verify_outcome = verification_result.get("summary", "Verification evaluated.")

                verify_log = self._record_step(
                    bug_id=bug_db_id,
                    attempt=attempt_num,
                    action="verify",
                    diff=diff_applied,
                    outcome=verify_outcome,
                    verified=is_verified,
                )
                if step_callback:
                    step_callback(verify_log)

                if is_verified:
                    self.state.current_code = patched_candidate
                    self.state.is_verified = True

                    # Record verified fix in DB
                    if bug_db_id:
                        db_fix = Fix(
                            bug_id=bug_db_id,
                            diff_text=diff_applied,
                            patched_code=patched_candidate,
                            rationale=fix_data.get("rationale", "Verified by Agentic Debugger"),
                            status="verified",
                        )
                        self.db.add(db_fix)
                        self.db.commit()
                    break

                # 5. RETRY EVALUATION
                # -----------------------------------------------
                should_retry, feedback = RetryPolicy.should_retry(self.state)
                if not should_retry:
                    self._record_step(
                        bug_id=bug_db_id,
                        attempt=attempt_num,
                        action="retry",
                        outcome=f"Stopping retry loop: {feedback}. Marked for manual developer review.",
                        verified=False,
                    )
                    break
                else:
                    self.state.custom_feedback = feedback
                    self._record_step(
                        bug_id=bug_db_id,
                        attempt=attempt_num,
                        action="retry",
                        outcome=f"Initiating retry attempt {attempt_num + 1}/{self.state.max_retries} with error feedback.",
                        verified=False,
                    )

        self.state.is_completed = True
        return self.state

    def _record_step(
        self,
        bug_id: Optional[int],
        attempt: int,
        action: str,
        outcome: str,
        diff: Optional[str] = None,
        verified: bool = False,
    ) -> AgentAttempt:
        """Persists step in DB and in-memory history."""
        attempt_obj = AgentAttempt(
            attempt_number=attempt,
            action=action,
            diff=diff,
            observation=outcome,
            is_verified=verified,
        )
        self.state.history.append(attempt_obj)

        try:
            db_run = AgenticRun(
                submission_id=self.state.submission_id,
                bug_id=bug_id,
                attempt_number=attempt,
                action_taken=action,
                diff_applied=diff,
                outcome=outcome,
                verified=verified,
            )
            self.db.add(db_run)
            self.db.commit()
        except Exception as e:
            logger.warning("Failed to commit agentic run step to DB: %s", str(e))
            self.db.rollback()

        return attempt_obj
