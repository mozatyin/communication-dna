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
2. Use the transition relationships to order the conversation flow
3. Completed intentions should be mentioned as things already done
4. The conversation should feel natural, not like an interrogation
5. Include both the speaker and an advisor/friend as dialogue partner
6. Format as "Speaker: ..." and "Advisor: ..." alternating turns
7. Generate 8-15 turns total
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
