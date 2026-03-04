"""PRD Generator: Produce structured game design PRDs from conversation history.

Uses IntentionGraph to decode user intentions, then calls an LLM to produce
a structured PRD document matching the 4-section format defined in PRD_GENERATION_GUIDE.md.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

import anthropic

from intention_graph.detector import IntentionDetector
from intention_graph.models import IntentionGraph


_PRD_SYSTEM_PROMPT = """\
You are an expert game designer writing a PRD (Product Requirements Document).

Given a conversation between a user and an AI host about game design, plus extracted \
intention data and game facts, produce a structured PRD document.

## Output Format

Your response MUST contain exactly two XML blocks:

<prd>
(The full PRD in Markdown, following the section structure below)
</prd>

<summary>
(A 2-3 sentence summary of the game concept)
</summary>

## PRD Section Structure (MANDATORY — include ALL 4 sections)

## 1. 游戏总览
- 游戏体验：What the game feels like to play — write as if you're pitching \
  the fantasy to a player: "You are a...", "You will feel..."
- 类型与视角：Genre, perspective, art style
- 乐趣与吸引力：Why players would enjoy this — name specific emotional hooks

## 2. 核心游戏循环
- 玩家的即时操作：Describe a concrete 60-second gameplay moment in present tense. \
  What does the player SEE on screen, what buttons do they press, what happens next?
- 胜利/失败/进程条件：Win/lose/progress conditions with specific thresholds if mentioned
- 循环的演变、升级与持续吸引力：How the player's experience changes from hour 1 to hour 100

## 3. 游戏系统
For EACH system (3-10 systems depending on game complexity):

### [System Name]
**如何运作**: Describe from the PLAYER'S perspective — "You open the menu, \
you pick a fruit, you see your character transform..." NOT "The system provides..."
**为何感觉良好**: Name the specific emotion or sensation — anticipation, \
surprise, mastery, pride. Include a concrete "moment" example.
**设计考量**: Identify 1-2 key design QUESTIONS phrased with question marks \
(e.g. "How rare should X be?" / "X应该多稀有？"), then provide a trade-off \
analysis and a concrete recommendation with numbers. Format: \
"Question? If A, then B; if C, then D. Recommendation: [specific suggestion]." \
Every 设计考量 MUST contain at least one "?" or "？".
**如何连接**: Describe how the player EXPERIENCES the connection — \
"After finishing a raid, you notice your fruit ability now has a new glow effect" \
NOT "Integrates with the raid system through reward mechanics". \
BANNED phrases: "synergize", "synergizes", "synergy", "directly influences", \
"feeds into", "gating X behind Y", "essential for progression", "ensures", \
"complements", "reinforces".

CRITICAL — [INFERRED] rule:
- ONLY add [INFERRED] if the system was NEVER mentioned or described by the user \
  in the conversation, not even indirectly.
- If the user described it even briefly (e.g. "there are races like Shark, Angel"), \
  that system is NOT inferred — do NOT tag it.
- Before tagging [INFERRED], search the ENTIRE conversation for any mention of \
  that topic. If the user said ANYTHING about it, it is NOT inferred.
- [INFERRED] means "I the PRD writer added this system because it's logically \
  necessary, but the user never discussed it."
- Example: User says "theres a race system" → Race System is NOT [INFERRED]. \
  User never mentions tutorials → Tutorial System IS [INFERRED].

## 4. 美术与音效风格
- **视觉风格**: Art direction — reference specific visual comparisons if possible
- **色彩调性**: Color palette mood
- **动画**: List key animations the player will notice most
- **打击感与反馈**: Juice / game feel — describe what the player FEELS on each action
- **UI 视觉语言**: UI style
- **音效**: Sound effects — describe the actual sounds (onomatopoeia welcome)
- **音乐**: Music direction — mood, instruments, how it shifts with gameplay
- **占位策略**: Placeholder asset strategy for dev team

## Rules

1. PLAYER EXPERIENCE ONLY — write as if describing the game TO a player. \
   Use "you" language: "you press", "you see", "you feel". \
   NEVER use technical language like "integrates with", "scales with", \
   "system provides", "triggers event", "links to", "feeds into", \
   "making X essential for Y progression". \
   NO implementation details (no "use Unity", "store in database", etc.)
2. CONCRETE MOMENTS — for every system, include at least one specific gameplay \
   scenario. Not "combat feels impactful" but "you land a charged sword slash \
   on a boss, the screen freezes for a split second, damage numbers fly out, \
   and the boss staggers backward."
3. FAITHFUL TO USER — use the exact terms, names, and numbers the user gave. \
   If the user said "13 islands" write "13 islands", not "multiple islands". \
   If the user said "level 1-700" write those exact numbers. \
   Do NOT invent proper names that the user never said: \
   - NO invented fruit names (not "Flame-Flame Fruit" — say "a fire-type Natural fruit") \
   - NO invented boss names (not "Darkbeard" — say "a powerful raid boss") \
   - NO invented ability names (not "Fire Fist" or "Air Slash" — say \
     "your fruit's ranged fire attack" or "a projectile sword technique") \
   - NO invented island names (not "Orange Town" — say "a level 15-25 island") \
   You MAY use descriptive phrases: "your fire fruit's area attack" is fine. \
   You MAY reference categories the user gave: "Natural", "Beast", "Paramecia".
4. Write the ENTIRE PRD in the SAME LANGUAGE as the conversation. \
   If the conversation is in Chinese, write Chinese. If English, write English.
5. Prioritize the user's core intention (end_goal from the intention graph) — \
   the PRD should serve that vision above all
6. High-confidence intentions from the graph should be reflected prominently; \
   low-confidence ones can be noted but shouldn't dominate
7. Section headers (## 1. through ## 4.) must use the Chinese titles shown above \
   regardless of conversation language, for downstream compatibility
8. Be GENEROUS with detail — a longer, more specific PRD is better than a \
   concise but vague one. Aim for 6000-10000 characters minimum.
9. AVOID REDUNDANCY — merge closely related mechanics into cohesive systems. \
   For example: Fighting Styles should be part of the Combat system, not separate. \
   Factions should be part of the PvP system. Currency/shops should be part of \
   the Economy system. Aim for 5-8 well-developed systems rather than 10+ thin ones.
10. INFER WISELY — if the game clearly needs systems the user didn't discuss \
    (e.g. Tutorial, Onboarding, Sailing/Navigation for an ocean game), add them \
    with [INFERRED] tag. A good PRD anticipates what's needed beyond what was said.
11. SELF-CHECK before returning — scan your output for banned phrases \
    (synergize, synergy, directly influences, feeds into, gating, ensures, \
    complements, reinforces, integrates). Replace any found with \
    player-experience language.
"""

_MAX_CONVERSATION_CHARS = 50000
_MAX_CONVERSATION_MESSAGES = 40


def _truncate_conversation(
    history: list[dict[str, str]],
) -> list[dict[str, str]]:
    """Keep last N messages within character budget."""
    if len(history) > _MAX_CONVERSATION_MESSAGES:
        history = history[-_MAX_CONVERSATION_MESSAGES:]

    total = sum(len(m.get("content", "")) for m in history)
    while total > _MAX_CONVERSATION_CHARS and len(history) > 2:
        removed = history.pop(0)
        total -= len(removed.get("content", ""))

    return history


def _conversation_to_dialogue(history: list[dict[str, str]]) -> str:
    """Convert message list to dialogue transcript string."""
    lines = []
    for msg in history:
        role = msg.get("role", "user")
        label = "User" if role == "user" else "Host"
        content = msg.get("content", "").strip()
        if content:
            lines.append(f"{label}: {content}")
    return "\n".join(lines)


def _graph_to_context(graph: IntentionGraph) -> str:
    """Serialize IntentionGraph into text context for the LLM prompt."""
    parts = []

    if graph.end_goal:
        end_node = next((n for n in graph.nodes if n.id == graph.end_goal), None)
        if end_node:
            parts.append(f"Core Intention (end goal): {end_node.text} "
                         f"[confidence={end_node.confidence:.2f}]")

    if graph.nodes:
        parts.append("\nExtracted Intentions:")
        for node in graph.nodes:
            marker = " (END GOAL)" if node.id == graph.end_goal else ""
            parts.append(
                f"  - [{node.id}] {node.text} "
                f"(confidence={node.confidence:.2f}, "
                f"specificity={node.specificity:.2f}, "
                f"source={node.source}){marker}"
            )

    if graph.transitions:
        parts.append("\nIntention Relationships:")
        for t in graph.transitions:
            parts.append(
                f"  - {t.from_id} --[{t.relation}]--> {t.to_id} "
                f"(probability={t.base_probability:.2f})"
            )

    if graph.summary:
        parts.append(f"\nGraph Summary: {graph.summary}")

    return "\n".join(parts)


def _parse_prd_response(raw: str) -> tuple[str, str]:
    """Extract <prd> and <summary> blocks from LLM response.

    Returns (prd_document, prd_summary).
    Falls back gracefully if tags are missing.
    """
    # Try <prd>...</prd>
    prd_match = re.search(r"<prd>(.*?)</prd>", raw, re.DOTALL)
    prd_document = prd_match.group(1).strip() if prd_match else ""

    # Try <summary>...</summary>
    summary_match = re.search(r"<summary>(.*?)</summary>", raw, re.DOTALL)
    prd_summary = summary_match.group(1).strip() if summary_match else ""

    # Fallback: if no <prd> tags, use the whole response as the PRD
    if not prd_document:
        # Strip any <summary> block from the raw text
        fallback = re.sub(r"<summary>.*?</summary>", "", raw, flags=re.DOTALL).strip()
        if fallback:
            prd_document = fallback

    # Fallback for summary: take first 2 sentences from PRD
    if not prd_summary and prd_document:
        sentences = re.split(r"[。.!！]", prd_document)
        prd_summary = "。".join(s.strip() for s in sentences[:2] if s.strip())
        if prd_summary:
            prd_summary += "。"

    return prd_document, prd_summary


class PrdGenerator:
    """Generate structured game design PRDs from conversation history.

    Uses IntentionGraph to decode user intentions, then calls an LLM
    to produce the final PRD document.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
    ):
        kwargs: dict = {"api_key": api_key}
        if api_key.startswith("sk-or-"):
            kwargs["base_url"] = "https://openrouter.ai/api"
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model
        self._detector = IntentionDetector(api_key=api_key, model=model)

    async def generate(
        self,
        game: Any,
        conversation_history: list[dict[str, str]],
        session_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Async interface per PRD guide spec.

        Args:
            game: Game instance (uses getattr(game, 'facts', []))
            conversation_history: List of {"role": "user"/"host", "content": "..."}
            session_info: {"uid": ..., "session_id": ..., "language": "zh"/"en"/...}

        Returns:
            {"prd_document": str, "prd_summary": str, "metadata": dict}
        """
        return await asyncio.to_thread(
            self._generate_sync, game, conversation_history, session_info
        )

    def generate_sync(
        self,
        game: Any,
        conversation_history: list[dict[str, str]],
        session_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Sync convenience method."""
        return self._generate_sync(game, conversation_history, session_info)

    def _generate_sync(
        self,
        game: Any,
        conversation_history: list[dict[str, str]],
        session_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Core pipeline: truncate → IG → LLM → parse."""
        # Step 1: Truncate conversation
        history = _truncate_conversation(list(conversation_history))
        dialogue = _conversation_to_dialogue(history)

        # Step 2: Extract game facts
        facts = getattr(game, "facts", []) if game else []

        # Step 3: Run IntentionGraph analysis (non-fatal)
        ig_context = ""
        ig_available = False
        core_intention = ""
        num_intentions = 0
        graph = None

        try:
            graph = self._detector.analyze(
                text=dialogue,
                speaker_id="user",
                speaker_label="User",
                domain="product",
                skip_expand=False,
                skip_clarify=True,
            )
            if graph and graph.nodes:
                ig_context = _graph_to_context(graph)
                ig_available = True
                num_intentions = len(graph.nodes)
                if graph.end_goal:
                    end_node = next(
                        (n for n in graph.nodes if n.id == graph.end_goal), None
                    )
                    if end_node:
                        core_intention = end_node.text
        except Exception:
            # IG extraction failure is non-fatal
            pass

        # Step 4: Build LLM prompt
        language = session_info.get("language", "zh") if session_info else "zh"

        user_parts = []
        user_parts.append("## Conversation History\n")
        user_parts.append(dialogue)

        if facts:
            user_parts.append("\n\n## Game Facts\n")
            for fact in facts:
                user_parts.append(f"- {fact}")

        if ig_context:
            user_parts.append("\n\n## Intention Graph Analysis\n")
            user_parts.append(ig_context)

        user_parts.append(f"\n\n## Language\n\nWrite the PRD in: {language}")

        user_message = "\n".join(user_parts)

        # Step 5: Call LLM
        response = self._client.messages.create(
            model=self._model,
            max_tokens=8000,
            temperature=0.7,
            system=_PRD_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text

        # Step 6: Parse response
        prd_document, prd_summary = _parse_prd_response(raw)

        # Step 7: Build metadata
        metadata = {
            "core_intention": core_intention,
            "num_intentions": num_intentions,
            "num_facts": len(facts),
            "ig_available": ig_available,
            "language": language,
            "model": self._model,
        }

        return {
            "prd_document": prd_document,
            "prd_summary": prd_summary,
            "metadata": metadata,
        }
