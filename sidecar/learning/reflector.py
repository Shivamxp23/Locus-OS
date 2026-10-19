"""
SPEC §1.7 + §10.1: Post-Turn Background Review Subsystem (F-0007).
Spawns background daemon thread for memory/skill extraction with strict tool whitelisting,
skill update preference hierarchy, and error containment ("never fatal").
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

import sidecar.config as config
from sidecar.providers.post_turn import (
    ALLOWED_REVIEW_TOOLS,
    BasePostTurnProvider,
    PostTurnReviewResult,
    SkillUpdatePreference,
)

logger = logging.getLogger(__name__)

MEMORY_REVIEW_PROMPT = (
    "MEMORY REVIEW: Examine the recent conversation snapshot. Has the user revealed:\n"
    "- Explicit user preferences, constraints, or stylistic rules?\n"
    "- Personal details, workflow patterns, project facts, or domain specifics?\n"
    "If so, formulate concise memory items to persist."
)

SKILL_REVIEW_PROMPT = (
    "SKILL REVIEW: Should any skill be saved, updated, or patched based on successful patterns or user corrections?\n"
    "Strict preference order:\n"
    "1. UPDATE A CURRENTLY-LOADED SKILL (the one in play this session)\n"
    "2. UPDATE AN EXISTING UMBRELLA (via skills_list + skill_view)\n"
    "3. ADD A SUPPORT FILE under an existing umbrella (references/, templates/, scripts/)\n"
    "4. CREATE A NEW CLASS-LEVEL UMBRELLA SKILL (only when nothing fits)\n"
    "Key invariant: prefer extending existing skills over creating new ones."
)


class PostTurnReviewer(BasePostTurnProvider):
    """
    Concrete implementation of Post-Turn Background Review.
    Executes on a daemon thread without blocking the primary conversation.
    Enforces strict tool whitelisting and contains all errors to never crash a session.
    """

    _shared_reviews: Dict[str, PostTurnReviewResult] = {}
    _shared_lock = threading.Lock()

    def __init__(
        self,
        custom_config: Optional[Dict[str, Any]] = None,
        mock_runner: Optional[Callable[[str, List[Dict[str, Any]]], Dict[str, Any]]] = None,
    ) -> None:
        self.custom_config = custom_config or {}
        self.mock_runner = mock_runner
        self._completed_reviews = self._shared_reviews
        self._lock = self._shared_lock

    def is_enabled(self) -> bool:
        """Check if post-turn review is enabled, defaulting to True unless explicitly disabled."""
        if "locus.post_turn_review.enabled" in self.custom_config:
            return bool(self.custom_config["locus.post_turn_review.enabled"])
        val = config.get("locus.post_turn_review.enabled")
        if val is not None and not config.is_enabled("locus.post_turn_review.enabled"):
            return False
        return True

    def is_tool_allowed(self, tool_name: str) -> bool:
        """
        Enforce strict tool whitelist per SPEC §1.7 lines 2883-2887.
        Only 'memory', 'skill_manage', 'locus_memory', and 'locus_vault' are permitted.
        All other tools (terminal, write_file, browser, edit) are strictly DENIED.
        """
        if not tool_name or not isinstance(tool_name, str):
            return False
        return tool_name.strip() in ALLOWED_REVIEW_TOOLS

    def filter_tools(self, tool_names: List[str]) -> List[str]:
        """Filter a list of tool names, stripping any tool not in the whitelist."""
        if not tool_names:
            return []
        return [t for t in tool_names if self.is_tool_allowed(t)]

    def get_skill_preferences(self) -> List[str]:
        """Return the 4-tier skill preference hierarchy per SPEC §1.7 lines 2889-2895."""
        return [
            SkillUpdatePreference.UPDATE_CURRENTLY_LOADED.value,
            SkillUpdatePreference.UPDATE_EXISTING_UMBRELLA.value,
            SkillUpdatePreference.ADD_SUPPORT_FILE.value,
            SkillUpdatePreference.CREATE_NEW_UMBRELLA.value,
        ]

    def build_review_prompt(self, conversation_snapshot: List[Dict[str, Any]]) -> str:
        """
        Build the combined memory and skill review prompt per SPEC §1.7 lines 2867-2871.
        """
        lines = [
            "=== POST-TURN BACKGROUND REVIEW PROMPT ===",
            MEMORY_REVIEW_PROMPT,
            "",
            SKILL_REVIEW_PROMPT,
            "",
            "TOOL RESTRICTIONS:",
            f"You ONLY have access to the following tools: {', '.join(ALLOWED_REVIEW_TOOLS)}.",
            "All other tools (terminal, bash, file modification, browser) are strictly DENIED.",
            "",
            f"CONVERSATION SNAPSHOT ({len(conversation_snapshot)} messages):",
        ]
        for idx, msg in enumerate(conversation_snapshot):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            lines.append(f"[{idx+1}] {role}: {content}")
        return "\n".join(lines)

    def spawn_background_review(
        self,
        conversation_snapshot: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        sync: bool = False,
    ) -> PostTurnReviewResult:
        """
        Fork a daemon background review task on a separate thread (or sync if requested).
        Never blocks the main conversation turn (SPEC §1.7 line 2855 & line 2877).
        """
        review_id = f"rev-{uuid.uuid4().hex[:8]}"
        sid = session_id or f"sess-{uuid.uuid4().hex[:6]}"

        if not self.is_enabled():
            result = PostTurnReviewResult(
                review_id=review_id,
                session_id=sid,
                status="disabled",
                execution_mode="sync" if sync else "background_thread",
            )
            with self._lock:
                self._completed_reviews[review_id] = result
            return result

        if sync:
            return self._execute_review(review_id, sid, conversation_snapshot)

        # SPEC §1.7 line 2875: thread = daemon_thread(target=..., args=[...]); thread.start()
        # Thread runs in background. Main conversation continues immediately.
        thread = threading.Thread(
            target=self._execute_review,
            args=(review_id, sid, conversation_snapshot),
            daemon=True,
            name=f"post-turn-review-{review_id}",
        )
        thread.start()

        dispatched_result = PostTurnReviewResult(
            review_id=review_id,
            session_id=sid,
            status="dispatched",
            execution_mode="background_thread",
        )
        with self._lock:
            self._completed_reviews[review_id] = dispatched_result
        return dispatched_result

    def _execute_review(
        self,
        review_id: str,
        session_id: str,
        conversation_snapshot: List[Dict[str, Any]],
    ) -> PostTurnReviewResult:
        """
        Execute review logic with absolute error containment ("never fatal" guarantee).
        """
        start_time = time.time()
        try:
            prompt = self.build_review_prompt(conversation_snapshot)
            memory_insights: List[Dict[str, Any]] = []
            skill_updates: List[Dict[str, Any]] = []
            denied_tools_attempted: List[str] = []

            if self.mock_runner:
                custom_res = self.mock_runner(prompt, conversation_snapshot)
                memory_insights = custom_res.get("memory_insights", [])
                skill_updates = custom_res.get("skill_updates", [])
                raw_tool_attempts = custom_res.get("tools_attempted", [])
                for t in raw_tool_attempts:
                    if not self.is_tool_allowed(t):
                        denied_tools_attempted.append(t)
            else:
                # Standard heuristic extraction
                for msg in conversation_snapshot:
                    content = str(msg.get("content", ""))
                    content_lower = content.lower()
                    # Check for memory cues
                    if any(cue in content_lower for cue in ["prefer", "always", "never", "my name is", "remember", "rule"]):
                        memory_insights.append({
                            "type": "preference_or_rule",
                            "source_role": msg.get("role", "user"),
                            "snippet": content[:120],
                        })
                    # Check for skill cues
                    if any(cue in content_lower for cue in ["skill", "workflow", "script", "template"]):
                        skill_updates.append({
                            "preference_tier": SkillUpdatePreference.UPDATE_CURRENTLY_LOADED.value,
                            "target": "active_or_umbrella_skill",
                            "rationale": content[:120],
                        })
                    # Check if illegal tools were referenced / attempted
                    for unapproved in ["bash", "terminal", "write_file", "browser", "exec"]:
                        if f"{unapproved}(" in content_lower or f"tool:{unapproved}" in content_lower:
                            if unapproved not in denied_tools_attempted:
                                denied_tools_attempted.append(unapproved)

            duration_ms = (time.time() - start_time) * 1000.0
            result = PostTurnReviewResult(
                review_id=review_id,
                session_id=session_id,
                status="completed",
                memory_insights=memory_insights,
                skill_updates=skill_updates,
                denied_tools_attempted=denied_tools_attempted,
                execution_mode="sync" if threading.current_thread() is threading.main_thread() else "background_thread",
                duration_ms=duration_ms,
            )
            with self._lock:
                self._completed_reviews[review_id] = result
            return result

        except Exception as exc:
            # SPEC §1.7: "Never fatal" guarantee - review failures NEVER crash session
            logger.error(f"Post-turn review {review_id} failed gracefully: {exc}", exc_info=True)
            duration_ms = (time.time() - start_time) * 1000.0
            err_result = PostTurnReviewResult(
                review_id=review_id,
                session_id=session_id,
                status="error",
                memory_insights=[],
                skill_updates=[],
                denied_tools_attempted=[],
                execution_mode="sync" if threading.current_thread() is threading.main_thread() else "background_thread",
                duration_ms=duration_ms,
            )
            with self._lock:
                self._completed_reviews[review_id] = err_result
            return err_result

    def get_review_result(self, review_id: str) -> Optional[PostTurnReviewResult]:
        """Look up completed or dispatched review result by review_id."""
        with self._lock:
            return self._completed_reviews.get(review_id)
