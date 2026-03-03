"""Stage 2 — Expand: Decompose abstract intentions and complete paths."""

from __future__ import annotations

import json

import anthropic

from intention_graph.models import (
    ActionNode,
    IntentionGraph,
    Transition,
)


_EXPAND_SYSTEM_PROMPT = """\
You are an intention graph analyst performing two tasks:

1. DECOMPOSE: For abstract/high-level intentions (specificity < 0.5), break them into \
concrete sub-steps that a person would need to take.

2. PATH COMPLETE: For gaps between connected intentions, fill in missing intermediate steps \
that logically must exist.

Return ONLY valid JSON:
{
  "new_nodes": [
    {
      "id": "int_NNN",
      "text": "<concise action description>",
      "specificity": <float 0.0-1.0>,
      "parent_id": "<id of the node this decomposes from, or null>"
    }
  ],
  "new_transitions": [
    {
      "from_id": "<source>",
      "to_id": "<target>",
      "relation": "decomposes_to" | "next_step" | "enables",
      "base_probability": <float 0.0-1.0>,
      "confidence": <float 0.0-1.0>
    }
  ]
}

Guidelines:
- Only decompose nodes with specificity < 0.5
- New node IDs should continue from the highest existing ID
- Keep sub-steps concrete and actionable
- Do not over-expand: 2-5 sub-steps per abstract node is typical
- Path completion: if A connects to C but B must happen in between, add B
"""

# DNA feature adjustments: (feature_name, relation_type) -> probability delta
_DNA_ADJUSTMENTS: dict[tuple[str, str], float] = {
    ("directness", "next_step"): +0.10,
    ("directness", "alternative"): -0.05,
    ("hedging_frequency", "alternative"): +0.10,
    ("hedging_frequency", "next_step"): -0.05,
    ("vulnerability_willingness", "decomposes_to"): +0.05,
}


class Expand:
    """Stage 2: Expand abstract intentions into sub-steps and complete paths."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        kwargs: dict = {"api_key": api_key}
        if api_key.startswith("sk-or-"):
            kwargs["base_url"] = "https://openrouter.ai/api"
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model

    def run(
        self,
        graph: IntentionGraph,
        dna_features: dict[str, float] | None = None,
    ) -> IntentionGraph:
        """Expand the graph by decomposing abstract nodes and completing paths."""
        abstract_nodes = [n for n in graph.nodes if n.specificity < 0.5]
        if not abstract_nodes and len(graph.nodes) <= 1:
            return graph

        expansion = self._expand_graph(graph)

        existing_nodes = list(graph.nodes)
        existing_transitions = list(graph.transitions)

        domain = graph.nodes[0].domain if graph.nodes else "general"
        for new_node in expansion.get("new_nodes", []):
            existing_nodes.append(
                ActionNode(
                    id=new_node["id"],
                    text=new_node["text"],
                    domain=domain,
                    source="inferred",
                    status="pending",
                    confidence=0.7,
                    specificity=_clamp(new_node.get("specificity", 0.6)),
                )
            )

        for new_t in expansion.get("new_transitions", []):
            base_prob = _clamp(new_t["base_probability"])
            dna_adj = _apply_dna_adjustment(
                base_prob, new_t["relation"], dna_features or {}
            )
            existing_transitions.append(
                Transition(
                    from_id=new_t["from_id"],
                    to_id=new_t["to_id"],
                    base_probability=base_prob,
                    dna_adjusted_probability=dna_adj,
                    relation=new_t["relation"],
                    confidence=_clamp(new_t["confidence"]),
                )
            )

        if dna_features:
            adjusted_transitions = []
            for t in existing_transitions:
                if t.dna_adjusted_probability == t.base_probability:
                    adj = _apply_dna_adjustment(t.base_probability, t.relation, dna_features)
                    t = Transition(
                        from_id=t.from_id, to_id=t.to_id,
                        base_probability=t.base_probability,
                        dna_adjusted_probability=adj,
                        relation=t.relation, confidence=t.confidence,
                    )
                adjusted_transitions.append(t)
            existing_transitions = adjusted_transitions

        return IntentionGraph(
            nodes=existing_nodes,
            transitions=existing_transitions,
            end_goal=graph.end_goal,
            dna_profile_id=graph.dna_profile_id,
            completed_path=graph.completed_path,
            evolution_history=graph.evolution_history,
            summary=f"Expanded graph: {len(existing_nodes)} nodes, {len(existing_transitions)} transitions.",
        )

    def _expand_graph(self, graph: IntentionGraph) -> dict:
        nodes_json = json.dumps(
            [{"id": n.id, "text": n.text, "specificity": n.specificity, "status": n.status}
             for n in graph.nodes],
            indent=2,
        )
        transitions_json = json.dumps(
            [{"from_id": t.from_id, "to_id": t.to_id, "relation": t.relation}
             for t in graph.transitions],
            indent=2,
        )
        user_message = (
            f"## Current Intention Graph\n\n"
            f"### Nodes\n{nodes_json}\n\n"
            f"### Transitions\n{transitions_json}\n\n"
            f"Decompose abstract nodes (specificity < 0.5) and fill path gaps. "
            f"The highest existing node ID is int_{len(graph.nodes):03d}. "
            f"Start new IDs from int_{len(graph.nodes) + 1:03d}."
        )
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=_EXPAND_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text
        return _parse_expand_response(raw)


def _apply_dna_adjustment(
    base_prob: float, relation: str, dna_features: dict[str, float]
) -> float:
    """Adjust a transition probability based on DNA personality features."""
    if not dna_features:
        return base_prob
    adjusted = base_prob
    for (feat_name, rel_type), delta in _DNA_ADJUSTMENTS.items():
        if rel_type == relation and feat_name in dna_features:
            feature_val = dna_features[feat_name]
            extremity = abs(feature_val - 0.5) * 2
            direction = 1.0 if feature_val > 0.5 else -1.0
            adjusted += delta * extremity * direction
    return _clamp(adjusted)


def _parse_expand_response(raw: str) -> dict:
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    start = raw.find("{")
    last = raw.rfind("}")
    if start != -1 and last != -1:
        try:
            return json.loads(raw[start:last + 1])
        except json.JSONDecodeError:
            pass
    return {"new_nodes": [], "new_transitions": []}


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))
