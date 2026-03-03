"""Stage 1 — Connect: Extract intention nodes and infer transitions from dialogue."""

from __future__ import annotations

import json
import re

import anthropic

from intention_graph.models import (
    ActionNode,
    Evidence,
    IntentionGraph,
    Transition,
)


_EXTRACT_SYSTEM_PROMPT = """\
You are an intention graph analyst. Given a conversation transcript and a target speaker, \
extract all concrete behavioral intentions expressed by that speaker.

A "concrete behavioral intention" is an action the speaker wants to take, is considering, \
or has already done. It must have a clear goal and be executable.

Return ONLY valid JSON with this structure:
{
  "reasoning": [
    {"node": "<short label>", "observations": ["quote or pattern from text"]}
  ],
  "nodes": [
    {
      "id": "int_001",
      "text": "<concise description of the intention>",
      "confidence": <float 0.0-1.0>,
      "specificity": <float 0.0-1.0>,
      "status": "pending" | "completed",
      "evidence": [{"quote": "<exact quote>", "utterance_index": <int>}]
    }
  ],
  "key_intention": "<id of the most central intention>",
  "inferred_end_goal": "<id of the likely ultimate goal, or null>",
  "domain": "<auto-detected domain: career, relationship, shopping, therapy, etc.>"
}

Guidelines:
- confidence: based on language certainty cues ("must/definitely" = high, "maybe/perhaps" = low)
- specificity: 0.0 = very abstract ("improve life"), 1.0 = fully specified ("apply to Google as PM by March")
- status: "completed" if speaker says they already did it, otherwise "pending"
- Only extract intentions for the target speaker, not other participants
- Number IDs sequentially: int_001, int_002, etc.
"""

_TRANSITIONS_SYSTEM_PROMPT = """\
You are an intention graph analyst. Given a list of extracted intention nodes from a conversation, \
infer the relationships and transition probabilities between them.

Return ONLY valid JSON with this structure:
{
  "transitions": [
    {
      "from_id": "<source node id>",
      "to_id": "<target node id>",
      "relation": "next_step" | "decomposes_to" | "alternative" | "enables" | "evolves_to",
      "base_probability": <float 0.0-1.0>,
      "confidence": <float 0.0-1.0>
    }
  ]
}

Relation types:
- next_step: sequential action (A then B)
- decomposes_to: A is a parent goal that breaks down into B
- alternative: A and B are mutually exclusive paths
- enables: A must happen before B is possible
- evolves_to: A may transform into B over time

Guidelines:
- base_probability: how likely the speaker would walk from A to B
  Use language cues: "definitely" → 0.8+, "maybe" → 0.3-0.5, "considering" → 0.4-0.6
- Only create edges with evidence. Do not over-connect.
- A node can have multiple outgoing transitions (branches).
"""


class Connect:
    """Stage 1: Extract intention nodes and transitions from dialogue."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        kwargs: dict = {"api_key": api_key}
        if api_key.startswith("sk-or-"):
            kwargs["base_url"] = "https://openrouter.ai/api"
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model

    def run(
        self,
        text: str,
        speaker_id: str,
        speaker_label: str,
        domain: str = "",
    ) -> IntentionGraph:
        """Extract intention nodes and transitions from dialogue text."""
        # Step 1a: Extract nodes
        nodes_data = self._extract_nodes(text, speaker_label, domain)

        # Step 1b: Infer transitions (if we have 2+ nodes)
        nodes = nodes_data["nodes"]
        transitions_data = []
        if len(nodes) >= 2:
            transitions_data = self._infer_transitions(text, speaker_label, nodes)

        # Build graph
        detected_domain = nodes_data.get("domain", domain or "general")
        action_nodes = [
            ActionNode(
                id=n["id"],
                text=n["text"],
                domain=detected_domain,
                source="expressed",
                status=n.get("status", "pending"),
                confidence=_clamp(n["confidence"]),
                specificity=_clamp(n["specificity"]),
                evidence=[
                    Evidence(
                        quote=e.get("quote", ""),
                        utterance_index=e.get("utterance_index", 0),
                        speaker=speaker_label,
                    )
                    for e in n.get("evidence", [])
                ],
            )
            for n in nodes
        ]

        transitions = [
            Transition(
                from_id=t["from_id"],
                to_id=t["to_id"],
                base_probability=_clamp(t["base_probability"]),
                dna_adjusted_probability=_clamp(t["base_probability"]),
                relation=t["relation"],
                confidence=_clamp(t["confidence"]),
            )
            for t in transitions_data
        ]

        return IntentionGraph(
            nodes=action_nodes,
            transitions=transitions,
            end_goal=nodes_data.get("inferred_end_goal") or nodes_data.get("key_intention"),
            summary=f"Extracted {len(action_nodes)} intentions from {speaker_label}'s dialogue.",
        )

    def _extract_nodes(self, text: str, speaker_label: str, domain: str) -> dict:
        domain_hint = f"\nDomain hint: {domain}" if domain else ""
        user_message = (
            f"## Conversation Transcript\n\n{text}\n\n"
            f"## Target Speaker\n\nExtract intentions for speaker labeled '{speaker_label}'.{domain_hint}\n\n"
            f"Return JSON with 'reasoning', 'nodes', 'key_intention', 'inferred_end_goal', and 'domain'."
        )
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=_EXTRACT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text
        return _parse_nodes_response(raw)

    def _infer_transitions(self, text: str, speaker_label: str, nodes: list[dict]) -> list[dict]:
        nodes_summary = json.dumps(
            [{"id": n["id"], "text": n["text"], "status": n.get("status", "pending")} for n in nodes],
            indent=2,
        )
        user_message = (
            f"## Conversation Transcript\n\n{text}\n\n"
            f"## Extracted Intention Nodes for '{speaker_label}'\n\n{nodes_summary}\n\n"
            f"Infer transitions between these nodes. Return JSON with 'transitions' array."
        )
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=_TRANSITIONS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text
        return _parse_transitions_response(raw)


def _parse_nodes_response(raw: str) -> dict:
    """Parse LLM response for node extraction."""
    raw = _strip_markdown_fences(raw)
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "nodes" in data:
            return data
    except json.JSONDecodeError:
        pass

    # Fallback: find outermost JSON object
    start = raw.find("{")
    last_brace = raw.rfind("}")
    if start != -1 and last_brace != -1:
        try:
            data = json.loads(raw[start:last_brace + 1])
            if isinstance(data, dict) and "nodes" in data:
                return data
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse nodes response: {raw[:200]}...")


def _parse_transitions_response(raw: str) -> list[dict]:
    """Parse LLM response for transition inference."""
    raw = _strip_markdown_fences(raw)
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "transitions" in data:
            return data["transitions"]
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Fallback: extract individual transition objects
    objects = []
    for m in re.finditer(r'\{[^{}]*\}', raw):
        try:
            obj = json.loads(m.group())
            if "from_id" in obj and "to_id" in obj:
                objects.append(obj)
        except json.JSONDecodeError:
            continue
    if objects:
        return objects

    raise ValueError(f"Could not parse transitions response: {raw[:200]}...")


def _strip_markdown_fences(raw: str) -> str:
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return raw


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))
