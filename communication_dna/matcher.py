"""Style Matcher: Guide conversations toward deeper, more meaningful expression."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import IntEnum

import anthropic

from communication_dna.models import CommunicationDNA
from communication_dna.speaker import _profile_to_style_instructions


class DepthLevel(IntEnum):
    """Conversation depth levels."""
    PLEASANTRY = 0
    FACTUAL = 1
    OPINION = 2
    EMOTIONAL = 3
    BELIEF = 4
    INSIGHT = 5


@dataclass
class MatcherResponse:
    """Response from the Style Matcher."""
    response_text: str
    assessed_depth: DepthLevel
    target_depth: DepthLevel
    strategy_used: str


_SYSTEM_PROMPT = """\
You are a conversation partner optimized for deep, meaningful dialogue.

Your goals:
1. Match the counterpart's communication style to build trust and lower defenses
2. Assess the current depth of self-disclosure in the conversation
3. Gently guide the conversation toward deeper self-expression
4. Maximize VALUE DENSITY — every response should invite substantive, meaningful replies

Depth levels:
- L0: Social pleasantries ("How are you?" "Fine.")
- L1: Factual statements ("I work in marketing")
- L2: Opinion expression ("I think this approach is wrong")
- L3: Emotional disclosure ("Honestly, I'm anxious about it")
- L4: Core beliefs ("I've always believed technology should serve people")
- L5: Self-insight ("I just realized I've been avoiding this issue")

Guide strategies:
- RECIPROCAL_DISCLOSURE: Share something at the target depth to invite matching disclosure
- SPECIFIC_QUESTION: Ask a specific, non-judgmental question about what they shared
- REFLECTIVE_VALIDATION: Reflect back what you heard and validate it, then deepen
- STRATEGIC_SILENCE: Give a brief, warm response that creates space for them to continue
- GENTLE_CHALLENGE: Respectfully invite them to examine an assumption or go deeper

CRITICAL: Never be judgmental. Never push too hard. If they resist going deeper, stay at their level and try again later.

Return JSON with keys:
- response_text: your response to the counterpart
- assessed_depth: integer 0-5, the current depth of the conversation
- target_depth: integer 0-5, the depth you're guiding toward (usually assessed + 1, max 5)
- strategy_used: which guide strategy you chose
"""


class StyleMatcher:
    """Guide conversations toward deeper expression while matching communication style."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        kwargs: dict = {"api_key": api_key}
        if api_key.startswith("sk-or-"):
            kwargs["base_url"] = "https://openrouter.ai/api"
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model

    def respond(
        self,
        counterpart: CommunicationDNA,
        conversation: list[dict],
        goal: str = "understand_deeper",
    ) -> MatcherResponse:
        """Generate a depth-optimized response matched to counterpart's style."""

        style_context = _profile_to_style_instructions(counterpart)
        depth_context = ""
        if counterpart.depth_profile:
            dp = counterpart.depth_profile
            depth_context = (
                f"\n\nCounterpart depth profile:\n"
                f"- Baseline depth: {dp.baseline_depth}\n"
                f"- Max observed: {dp.max_observed_depth}\n"
                f"- Warmup turns needed: {dp.disclosure_trajectory.warmup_turns if dp.disclosure_trajectory else 'unknown'}\n"
                f"- Effective triggers: {', '.join(t.type for t in dp.depth_triggers)}\n"
                f"- Barriers: {', '.join(b.type for b in dp.depth_barriers)}\n"
            )

        conversation_text = "\n".join(
            f"{msg['role'].upper()}: {msg['text']}" for msg in conversation
        )

        user_message = (
            f"## Counterpart Communication Style\n{style_context}\n"
            f"{depth_context}\n"
            f"## Conversation Goal\n{goal}\n\n"
            f"## Conversation So Far\n{conversation_text}\n\n"
            f"Generate your response. Return ONLY valid JSON."
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = json.loads(raw)

        return MatcherResponse(
            response_text=parsed["response_text"],
            assessed_depth=DepthLevel(int(parsed["assessed_depth"])),
            target_depth=DepthLevel(int(parsed["target_depth"])),
            strategy_used=parsed["strategy_used"],
        )
