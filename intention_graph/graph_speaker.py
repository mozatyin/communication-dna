# intention_graph/graph_speaker.py
"""Graph Speaker: Generate dialogue from a known IntentionGraph (for evaluation)."""

from __future__ import annotations

import json

import anthropic

from intention_graph.models import IntentionGraph


_SYSTEM_PROMPT = """\
You are a dialogue simulator. Given an intention graph describing a person's goals, \
generate a realistic two-person conversation where the speaker naturally expresses \
these intentions through dialogue.

Rules:
1. The speaker should express ALL the intentions listed, but naturally — not as a list
2. Completed intentions should be mentioned as things already done
3. The conversation should feel natural, not like an interrogation
4. Adapt the dialogue partner role to the domain:
   - therapy/counseling → "Speaker: ..." and "Therapist: ..."
   - product/software → "Speaker: ..." and "PM: ..."
   - daily/daily_conversation → "Speaker: ..." and "Friend: ..."
   - customer_service → "Speaker: ..." and "Agent: ..."
   - negotiation → "Speaker: ..." and "Advisor: ..."
   - career → "Speaker: ..." and "Coach: ..."
   - education → "Speaker: ..." and "Advisor: ..."
   - project_management → "Speaker: ..." and "Manager: ..."
   - medical → "Speaker: ..." and "Doctor: ..."
   - legal → "Speaker: ..." and "Attorney: ..."
   - other → "Speaker: ..." and "Advisor: ..."
5. Generate 8-15 turns total

CRITICAL — Express relationship types through specific language patterns:
- "enables" (A enables B = A is prerequisite for B): \
Use phrases like "I need to [A] first before I can [B]", \
"I can't [B] until [A] is done", "[A] is required for [B]"
- "alternative" (A and B are mutually exclusive options): \
Use phrases like "I could either [A] or [B]", "I'm torn between [A] and [B]", \
"one option is [A], another is [B]"
- "decomposes_to" (A breaks down into B as sub-task): \
Use phrases like "part of [A] is [B]", "one thing I need to do for [A] is [B]"
- "next_step" (A leads to B in sequence): \
Use phrases like "after [A], I'll [B]", "once [A] is done, then [B]", \
"the next step after [A] is [B]"
- "evolves_to" (A transforms into B): \
Use phrases like "[A] might eventually become [B]"

The speaker MUST use these linguistic patterns so the relationship types are \
clearly recoverable from the dialogue text.

6. Adapt dialogue style to the domain:
   - therapy: emotionally expressive, hesitant, self-reflective
   - product: structured, data-driven, uses technical terms
   - daily: casual, informal, uses slang and fillers
   - customer_service: frustrated but polite, escalation-focused
   - negotiation: strategic, conditional ("if you give me X, I can..."), BATNA references
   - career: aspirational, self-assessment language, timeline-focused
   - education: academic vocabulary, deadlines, methodology discussion
   - project_management: sprint/milestone language, dependency-aware, risk-focused
   - medical: symptom description, treatment history, concern about side effects
   - legal: formal, evidence-focused, rights-aware, precedent references
"""


class GraphSpeaker:
    """Generate simulated dialogue from a known IntentionGraph."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        kwargs: dict = {"api_key": api_key}
        if api_key.startswith("sk-or-"):
            kwargs["base_url"] = "https://openrouter.ai/api"
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model

    def generate(self, graph: IntentionGraph, prompt: str = "") -> str:
        """Generate a dialogue that expresses the intentions in the graph."""
        graph_description = self._graph_to_description(graph)
        user_message = (
            f"## Intention Graph\n\n{graph_description}\n\n"
            f"## Scenario\n\n{prompt or 'A person discussing their goals with an advisor.'}\n\n"
            f"Generate a natural conversation where the Speaker expresses these intentions."
        )
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    def _graph_to_description(self, graph: IntentionGraph) -> str:
        lines = [f"Domain: {graph.nodes[0].domain if graph.nodes else 'general'}"]
        if graph.end_goal:
            goal_node = next((n for n in graph.nodes if n.id == graph.end_goal), None)
            if goal_node:
                lines.append(f"End Goal: {goal_node.text}")

        lines.append("\nIntentions:")
        for n in graph.nodes:
            status = " [COMPLETED]" if n.status == "completed" else ""
            lines.append(
                f"- {n.text} (confidence={n.confidence}, specificity={n.specificity}){status}"
            )

        lines.append("\nRelationships:")
        node_map = {n.id: n.text for n in graph.nodes}
        for t in graph.transitions:
            from_text = node_map.get(t.from_id, t.from_id)
            to_text = node_map.get(t.to_id, t.to_id)
            lines.append(
                f"- '{from_text}' --[{t.relation}, p={t.base_probability}]--> '{to_text}'"
            )

        return "\n".join(lines)
