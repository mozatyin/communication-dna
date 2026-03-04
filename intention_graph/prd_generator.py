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
- 游戏体验：What the game feels like to play (one-paragraph vision)
- 类型与视角：Genre, perspective, art style
- 乐趣与吸引力：Why players would enjoy this

## 2. 核心游戏循环
- 玩家的即时操作：What the player DOES moment-to-moment
- 胜利/失败/进程条件：Win/lose/progress conditions
- 循环的演变、升级与持续吸引力：How the loop evolves over time

## 3. 游戏系统
For EACH system (3-8 systems typical):

### [System Name]
**如何运作**: How players interact with this system
**为何感觉良好**: Why this is fun / satisfying
**设计考量**: Key design constraints or trade-offs
**如何连接**: How this system connects to other systems

If a system was NOT explicitly mentioned by the user but is logically necessary, \
add [INFERRED] after the system name, e.g. "### 经济系统 [INFERRED]"

## 4. 美术与音效风格
- **视觉风格**: Art direction
- **色彩调性**: Color palette mood
- **动画**: Key animations
- **打击感与反馈**: Juice / game feel
- **UI 视觉语言**: UI style
- **音效**: Sound effects direction
- **音乐**: Music direction
- **占位策略**: Placeholder asset strategy

## Rules

1. PLAYER EXPERIENCE ONLY — describe what the player sees, hears, feels, does. \
   NO technical implementation details (no "use Unity", "store in database", etc.)
2. Every bullet must be concrete and specific, not vague platitudes
3. Write the ENTIRE PRD in the SAME LANGUAGE as the conversation. \
   If the conversation is in Chinese, write Chinese. If English, write English.
4. Prioritize the user's core intention (end_goal from the intention graph) — \
   the PRD should serve that vision above all
5. High-confidence intentions from the graph should be reflected prominently; \
   low-confidence ones can be noted but shouldn't dominate
6. Section headers (## 1. through ## 4.) must use the Chinese titles shown above \
   regardless of conversation language, for downstream compatibility
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
