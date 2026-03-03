"""Stage 3 — Clarify: Detect ambiguities and generate incisive questions."""

from __future__ import annotations

import json
import math

import anthropic

from intention_graph.models import Ambiguity, IntentionGraph


_CLARIFY_SYSTEM_PROMPT = """\
You are an expert at generating clarifying questions for ambiguous intentions. \
Given an intention graph with ambiguous branch points, generate a single \
"incisive question" for each ambiguity.

An incisive question must:
1. Eliminate >= 50% of possible paths with one answer
2. Be easy for the user to answer (no deep thought required)
3. Sound natural and conversational (not like a survey)
4. Not reveal the system's internal reasoning

Return ONLY valid JSON:
{
  "questions": [
    {
      "node_id": "<ambiguous node id>",
      "incisive_question": "<the question to ask>",
      "expected_answers": [
        {"answer": "<possible answer>", "eliminates": ["<branch_id>", ...]},
        {"answer": "<possible answer>", "eliminates": ["<branch_id>", ...]}
      ]
    }
  ]
}
"""


class Clarify:
    """Stage 3: Detect ambiguities and generate incisive questions."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        kwargs: dict = {"api_key": api_key}
        if api_key.startswith("sk-or-"):
            kwargs["base_url"] = "https://openrouter.ai/api"
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model

    def run(
        self,
        graph: IntentionGraph,
        prob_diff_threshold: float = 0.3,
    ) -> IntentionGraph:
        """Detect ambiguities and generate incisive questions."""
        raw_ambiguities = _detect_ambiguities(graph, prob_diff_threshold)

        if not raw_ambiguities:
            return IntentionGraph(
                nodes=graph.nodes,
                transitions=graph.transitions,
                end_goal=graph.end_goal,
                dna_profile_id=graph.dna_profile_id,
                completed_path=graph.completed_path,
                evolution_history=graph.evolution_history,
                ambiguities=[],
                summary=graph.summary,
            )

        # Generate incisive questions via LLM
        questions = self._generate_questions(graph, raw_ambiguities)

        ambiguities = []
        for amb in raw_ambiguities:
            q_match = next(
                (q for q in questions if q.get("node_id") == amb["node_id"]),
                None,
            )
            question_text = q_match["incisive_question"] if q_match else ""
            info_gain = _estimate_information_gain(amb, graph)
            ambiguities.append(
                Ambiguity(
                    node_id=amb["node_id"],
                    branches=amb["branches"],
                    incisive_question=question_text,
                    information_gain=min(1.0, info_gain),
                )
            )

        # Sort by information gain descending
        ambiguities.sort(key=lambda a: -a.information_gain)

        return IntentionGraph(
            nodes=graph.nodes,
            transitions=graph.transitions,
            end_goal=graph.end_goal,
            dna_profile_id=graph.dna_profile_id,
            completed_path=graph.completed_path,
            evolution_history=graph.evolution_history,
            ambiguities=ambiguities,
            summary=graph.summary,
        )

    def _generate_questions(self, graph: IntentionGraph, ambiguities: list[dict]) -> list[dict]:
        node_map = {n.id: n.text for n in graph.nodes}
        amb_descriptions = []
        for amb in ambiguities:
            branches_text = ", ".join(
                f"'{node_map.get(b, b)}'" for b in amb["branches"]
            )
            amb_descriptions.append(
                f"Node '{node_map.get(amb['node_id'], amb['node_id'])}' (id={amb['node_id']}) "
                f"branches to: {branches_text}"
            )

        user_message = (
            f"## Ambiguous Branch Points\n\n"
            + "\n".join(f"- {d}" for d in amb_descriptions)
            + "\n\nGenerate one incisive question per ambiguity."
        )
        response = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=_CLARIFY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text
        return _parse_clarify_response(raw)


def _detect_ambiguities(
    graph: IntentionGraph, prob_diff_threshold: float = 0.3
) -> list[dict]:
    """Find nodes with multiple outgoing transitions of similar probability."""
    # Group transitions by source node
    outgoing: dict[str, list] = {}
    for t in graph.transitions:
        outgoing.setdefault(t.from_id, []).append(t)

    ambiguities = []
    for node_id, transitions in outgoing.items():
        if len(transitions) < 2:
            continue
        # Sort by probability descending
        sorted_t = sorted(transitions, key=lambda t: -t.dna_adjusted_probability)
        max_prob = sorted_t[0].dna_adjusted_probability
        second_prob = sorted_t[1].dna_adjusted_probability
        # Ambiguous if the gap between top two is small
        if (max_prob - second_prob) < prob_diff_threshold:
            ambiguities.append({
                "node_id": node_id,
                "branches": [t.to_id for t in sorted_t],
                "probabilities": [t.dna_adjusted_probability for t in sorted_t],
            })
    return ambiguities


def _estimate_information_gain(ambiguity: dict, graph: IntentionGraph) -> float:
    """Estimate information gain from resolving this ambiguity (Shannon entropy)."""
    probs = ambiguity.get("probabilities", [])
    if not probs:
        return 0.0
    total = sum(probs)
    if total == 0:
        return 0.0
    normalized = [p / total for p in probs]
    entropy = -sum(p * math.log2(p) for p in normalized if p > 0)
    max_entropy = math.log2(len(probs)) if len(probs) > 1 else 1.0
    return entropy / max_entropy if max_entropy > 0 else 0.0


def _parse_clarify_response(raw: str) -> list[dict]:
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "questions" in data:
            return data["questions"]
    except json.JSONDecodeError:
        pass
    start = raw.find("{")
    last = raw.rfind("}")
    if start != -1 and last != -1:
        try:
            data = json.loads(raw[start:last + 1])
            if isinstance(data, dict) and "questions" in data:
                return data["questions"]
        except json.JSONDecodeError:
            pass
    return []
