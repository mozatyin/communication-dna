"""FactExtractor: Periodic extraction of facts, reality, secrets (V2.4).

Runs alongside ThinkSlow every N turns (adaptive frequency). Uses a separate
LLM call focused exclusively on factual information — NOT personality traits.
"""

from __future__ import annotations

import json

import anthropic

from super_brain.models import Fact, Reality, FactExtractionResult


_FACT_EXTRACTOR_SYSTEM = """\
You are analyzing a conversation to extract FACTUAL information about the target \
speaker (labeled "Person B"). Focus on concrete facts, NOT personality traits.

Extract:
1. **Facts**: Specific, concrete information (job, location, family, hobbies, education, etc.)
2. **Reality snapshot**: A brief narrative of their current life situation
3. **Secrets**: Things they avoid discussing, topics that change their energy, \
contradictions between what they say and how they say it
4. **Contradictions**: Statements that conflict with earlier statements

Return ONLY valid JSON:
{
  "facts": [
    {"category": "<category>", "content": "<what you learned>", "confidence": <0.0-1.0>}
  ],
  "reality": {
    "summary": "<1-2 sentence narrative of their current situation>",
    "domains": {"<domain>": "<description>", ...},
    "constraints": ["<limiting factor>", ...],
    "resources": ["<advantage or asset>", ...]
  },
  "secrets": ["<observation about avoidance or hidden pattern>", ...],
  "contradictions": ["<statement X conflicts with statement Y>", ...]
}

Categories for facts: career, relationship, hobby, education, location, family, \
preference, experience, health, financial.

IMPORTANT:
- Only extract facts with CLEAR evidence from the text. Do not infer or guess.
- Reality snapshot should be null if insufficient information.
- Secrets are OBSERVATIONS, not accusations. "Energy drops when family is mentioned" not "hiding something about family".
- Confidence: 0.5-0.7 for mentioned once, 0.8-0.9 for discussed in detail, 1.0 only for explicit statements.
"""


def _format_conversation(conversation: list[dict]) -> str:
    """Format conversation for FactExtractor input."""
    lines = []
    for msg in conversation:
        label = "Person A" if msg["role"] == "chatter" else "Person B"
        lines.append(f"{label}: {msg['text']}")
    return "\n\n".join(lines)


def _parse_fact_response(raw: str) -> dict:
    """Parse FactExtractor JSON response with fallback."""
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass
    return {"facts": [], "reality": None, "secrets": [], "contradictions": []}


def _deduplicate_facts(
    new_raw: list[dict],
    existing: list[Fact],
    current_turn: int,
) -> list[Fact]:
    """Deduplicate new facts against existing ones (case-insensitive content match)."""
    existing_contents = {f.content.lower().strip() for f in existing}
    unique: list[Fact] = []
    for raw_fact in new_raw:
        content = raw_fact.get("content", "").strip()
        if content.lower() not in existing_contents:
            unique.append(Fact(
                category=raw_fact.get("category", "unknown"),
                content=content,
                confidence=max(0.0, min(1.0, float(raw_fact.get("confidence", 0.5)))),
                source_turn=current_turn,
            ))
            existing_contents.add(content.lower())
    return unique


class FactExtractor:
    """Extracts facts, reality narrative, and secrets from conversation."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        kwargs: dict = {"api_key": api_key}
        if api_key.startswith("sk-or-"):
            kwargs["base_url"] = "https://openrouter.ai/api"
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model

    def extract(
        self,
        conversation: list[dict],
        existing_facts: list[Fact] | None = None,
        current_turn: int = 0,
    ) -> FactExtractionResult:
        """Extract facts, reality, secrets from conversation.

        Args:
            conversation: Full conversation so far.
            existing_facts: Previously extracted facts (for deduplication).
            current_turn: Current turn number (for fact source tracking).

        Returns:
            FactExtractionResult with new (deduplicated) facts, reality, secrets.
        """
        conv_text = _format_conversation(conversation)
        existing = existing_facts or []

        # Include existing facts context so LLM focuses on NEW information
        existing_section = ""
        if existing:
            known = [f"{f.category}: {f.content}" for f in existing]
            existing_section = (
                "\n\nALREADY KNOWN FACTS (focus on NEW information not listed here):\n"
                + "\n".join(f"- {k}" for k in known)
            )

        user_message = (
            f"## Conversation\n\n{conv_text}\n\n"
            f"## Target Speaker\n\nExtract factual information about Person B."
            f"{existing_section}\n\n"
            f"Return JSON with facts, reality, secrets, contradictions."
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=_FACT_EXTRACTOR_SYSTEM,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text
        data = _parse_fact_response(raw)

        # Deduplicate facts
        new_facts = _deduplicate_facts(
            data.get("facts", []), existing, current_turn,
        )

        # Build Reality if provided
        reality = None
        raw_reality = data.get("reality")
        if raw_reality and isinstance(raw_reality, dict) and raw_reality.get("summary"):
            reality = Reality(
                summary=raw_reality["summary"],
                domains=raw_reality.get("domains", {}),
                constraints=raw_reality.get("constraints", []),
                resources=raw_reality.get("resources", []),
            )

        return FactExtractionResult(
            new_facts=new_facts,
            reality=reality,
            secrets=data.get("secrets", []),
            contradictions=data.get("contradictions", []),
        )
