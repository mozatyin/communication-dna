"""Conductor module — selects the next conversation action.

The Conductor sits between ThinkFast (real-time signals) and ThinkSlow
(periodic personality extraction), choosing the optimal conversational
move based on a priority-ordered decision chain.

Priority order:
1. Early turns (trust-building) -> listen
2. ThinkFast detected an opening -> follow_thread
3. Info is stale + incisive questions available -> ask_incisive
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
    """

    def __init__(self, trust_building_turns: int = 3) -> None:
        self.trust_building_turns = trust_building_turns

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
            return ConductorAction(
                mode="listen",
                context="Trust-building phase — passive listening",
            )

        # Priority 2: ThinkFast detected a conversational opening
        if think_fast.opening:
            return ConductorAction(
                mode="follow_thread",
                context=think_fast.opening,
            )

        # Priority 3: Info is stale and we have incisive questions to ask
        if (
            think_fast.info_entropy < 0.3
            and think_slow is not None
            and think_slow.incisive_questions
        ):
            # Pick the highest-priority question
            top_question = max(
                think_slow.incisive_questions, key=lambda q: q.priority
            )
            return ConductorAction(
                mode="ask_incisive",
                context=f"Low info entropy ({think_fast.info_entropy:.2f}), "
                        f"targeting {top_question.target}",
                question=top_question.question,
            )

        # Priority 4: Default — keep listening
        return ConductorAction(
            mode="listen",
            context="No actionable signal — continue listening",
        )
