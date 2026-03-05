"""Conductor module — selects the next conversation action.

The Conductor sits between ThinkFast (real-time signals) and ThinkSlow
(periodic personality extraction), choosing the optimal conversational
move based on a priority-ordered decision chain with force-probing.

Priority order:
0. Force-probe — if no incisive question in N turns, force one
1. Early turns (trust-building) -> listen
2. ThinkFast detected an opening -> follow_thread
3. Info entropy < threshold + incisive questions available -> ask_incisive
4. Default -> listen
"""

from __future__ import annotations

from typing import Optional

from super_brain.models import (
    ConductorAction,
    ThinkFastResult,
    ThinkSlowResult,
)


class Conductor:
    """Selects the next conversation action based on ThinkFast/ThinkSlow signals.

    Parameters
    ----------
    trust_building_turns : int
        Number of initial turns dedicated to passive listening (default 3).
    max_turns_without_probe : int
        Force an incisive question if none asked in this many turns (default 4).
    entropy_threshold : float
        Info entropy below this triggers ask_incisive (default 0.5).
    """

    def __init__(
        self,
        trust_building_turns: int = 3,
        max_turns_without_probe: int = 4,
        entropy_threshold: float = 0.5,
    ) -> None:
        self.trust_building_turns = trust_building_turns
        self.max_turns_without_probe = max_turns_without_probe
        self.entropy_threshold = entropy_threshold
        self._turns_since_last_incisive = 0
        self._asked_targets: set[str] = set()

    def _pick_question(self, think_slow: ThinkSlowResult) -> tuple:
        """Pick the best incisive question, preferring unasked targets."""
        questions = think_slow.incisive_questions
        # Prefer questions targeting traits we haven't asked about yet
        unasked = [q for q in questions if q.target not in self._asked_targets]
        pool = unasked if unasked else questions
        top = max(pool, key=lambda q: q.priority)
        self._asked_targets.add(top.target)
        return top

    def decide(
        self,
        think_fast: ThinkFastResult,
        think_slow: Optional[ThinkSlowResult],
        turn_number: int,
    ) -> ConductorAction:
        """Select the next conversation action.

        Parameters
        ----------
        think_fast : ThinkFastResult
            Real-time signal from the latest exchange.
        think_slow : ThinkSlowResult | None
            Latest periodic personality extraction (may be None early on).
        turn_number : int
            Current turn number in the conversation (1-indexed).

        Returns
        -------
        ConductorAction
            The chosen action with mode, context, and optional question.
        """
        # Priority 1: Early turns — always listen to build trust
        if turn_number <= self.trust_building_turns:
            self._turns_since_last_incisive += 1
            return ConductorAction(
                mode="listen",
                context="Trust-building phase — passive listening",
            )

        # Priority 0 (highest after trust): Force-probe if too long without asking
        has_questions = (think_slow is not None and think_slow.incisive_questions)
        if (
            self._turns_since_last_incisive >= self.max_turns_without_probe
            and has_questions
        ):
            top_question = self._pick_question(think_slow)
            self._turns_since_last_incisive = 0
            return ConductorAction(
                mode="ask_incisive",
                context=f"Force-probe (no incisive in {self.max_turns_without_probe} turns), "
                        f"targeting {top_question.target}",
                question=top_question.question,
            )

        # Priority 2: ThinkFast detected a conversational opening
        if think_fast.opening:
            self._turns_since_last_incisive += 1
            return ConductorAction(
                mode="follow_thread",
                context=think_fast.opening,
            )

        # Priority 3: Info is below threshold and we have incisive questions to ask
        if (
            think_fast.info_entropy < self.entropy_threshold
            and has_questions
        ):
            top_question = self._pick_question(think_slow)
            self._turns_since_last_incisive = 0
            return ConductorAction(
                mode="ask_incisive",
                context=f"Low info entropy ({think_fast.info_entropy:.2f}), "
                        f"targeting {top_question.target}",
                question=top_question.question,
            )

        # Priority 4: Default — keep listening
        self._turns_since_last_incisive += 1
        return ConductorAction(
            mode="listen",
            context="No actionable signal — continue listening",
        )
