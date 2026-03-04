"""Stage 1 — Connect: Extract intention nodes and infer transitions from dialogue.

v0.6: Joint extraction with branching detection, decision-tree relation classification,
and contrastive few-shot examples.
"""

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


_SYSTEM_PROMPT = """\
You are an intention graph analyst. Given a conversation transcript and a target speaker, \
extract a complete intention graph: nodes (behavioral intentions) AND edges \
(relationships/transitions) between them, in a SINGLE analysis pass.

A "concrete behavioral intention" is an action the speaker wants to take, is considering, \
or has already done. It must have a clear goal and be executable.

## Reasoning Process (follow this order)

STEP 1 - IDENTIFY INTENTIONS:
Read the dialogue and list each concrete behavioral intention the target speaker expresses. \
For each, note the exact quote(s) that reveal it.

STEP 2 - IDENTIFY THE END GOAL:
The end goal is the speaker's ULTIMATE objective — what all other intentions serve.

Use these tests:
a) WHY CHAIN: For each intention, ask "why does the speaker want this?" \
   Keep asking until you reach an intention that is wanted for its own sake. That's the end goal.
b) CONVERGENCE TEST: Which intention do other intentions point toward? \
   If "save money" and "build portfolio" both serve "change career", then "change career" is the end goal.
c) FRAMING TEST: What did the speaker present as their main topic? \
   Often stated in the first few utterances as "I want to..." or "My goal is..."
d) ABSTRACTION TEST: The end goal is usually the MOST ABSTRACT intention (lowest specificity).

STEP 3 - IDENTIFY GRAPH TOPOLOGY:
Before mapping edges, determine the overall structure:

a) SEQUENTIAL: Speaker describes steps in order ("first X, then Y, then Z") → chain: X → Y → Z
b) FAN-OUT/BRANCHING: Speaker presents alternatives or parallel paths from one goal \
("I could either X or Y" / "there are two things I need to do") → star: Goal → X, Goal → Y
c) MIXED: Some sequential paths with branching points

KEY RULE: If the speaker presents options at the SAME LEVEL OF ABSTRACTION \
serving the SAME PARENT GOAL, these are alternatives branching FROM THE PARENT, \
not sequential steps between each other.
Example: "I want to fix things. I could talk to her, or give her space."
→ WRONG: talk → give_space (sequential chain)
→ RIGHT: fix_things → talk (alternative), fix_things → give_space (alternative)

STEP 4 - CLASSIFY EACH EDGE using this decision tree:

For each pair (A, B) where the dialogue reveals a connection:

Q1: Are A and B MUTUALLY EXCLUSIVE options serving the same goal?
    (Speaker says "either/or", "one option is... another is...", "I'm torn between...")
    → "alternative" — edge goes BETWEEN the two options OR from parent to each option

Q2: Is A a PREREQUISITE that must happen before B can start?
    (Speaker says "I need A first", "I can't B until A", "that requires A")
    → "enables" (direction: prerequisite A → dependent B)

Q3: Is B a SUB-TASK that is part of achieving goal A, AND the speaker needs ALL sub-tasks?
    (B is a specific step within A's scope; A is more abstract than B; \
    B is not an either/or option but a required component)
    → "decomposes_to" (direction: abstract parent A → concrete child B)
    DISTINGUISH FROM "alternative": If speaker presents multiple approaches as \
    either/or choices → use "alternative", not "decomposes_to".

Q4: Does A naturally lead to B in temporal sequence WITHOUT dependency?
    (Speaker says "after A, I'll do B" where B could happen without A)
    → "next_step"

Q5: Does A transform into B over time?
    (Speaker says "it might become...", "eventually...")
    → "evolves_to"

If none fit clearly → do NOT create this edge.

CRITICAL: Only create an edge if you can point to textual evidence. \
Prefer fewer high-confidence edges over many speculative ones.

STEP 5 - VERIFY:
- The end goal should be the most abstract, overarching intention
- Check edge directions: "A enables B" means A → B
- For "decomposes_to": parent must be MORE ABSTRACT (lower specificity) than child
- "alternative" edges should connect options at similar abstraction levels
- No self-loops. No impossible cycles (A enables B, B enables A)

Return ONLY valid JSON:
{
  "reasoning": {
    "node_observations": [
      {"label": "<short label>", "quotes": ["<quote1>"]}
    ],
    "end_goal_rationale": "<why this node is the end goal>",
    "edge_observations": [
      {"from": "<label>", "to": "<label>", "evidence": "<quote>", "relation": "<type>"}
    ]
  },
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
  "transitions": [
    {
      "from_id": "<source node id>",
      "to_id": "<target node id>",
      "relation": "next_step" | "decomposes_to" | "alternative" | "enables" | "evolves_to",
      "base_probability": <float 0.0-1.0>,
      "confidence": <float 0.0-1.0>
    }
  ],
  "end_goal": "<id of the ultimate goal node>",
  "domain": "<auto-detected domain: career, relationship, shopping, therapy, food, etc.>"
}

Guidelines:
- confidence: based on language certainty cues ("must/definitely" = high, "maybe/perhaps" = low)
- specificity: 0.0 = very abstract ("improve life"), 1.0 = fully specified ("apply to Google as PM by March")
- status: "completed" if speaker says they already did it, otherwise "pending"
- Only extract intentions for the target speaker, not other participants
- Number IDs sequentially: int_001, int_002, etc.
- base_probability: how likely the speaker would walk from A to B \
  ("definitely" → 0.8+, "maybe" → 0.3-0.5, "considering" → 0.4-0.6)
"""

_FEW_SHOT_EXAMPLES = """\

## Calibration Examples

### Example A — Decomposition chain (food ordering)

Dialogue:
Speaker: I'm craving sushi tonight. I think I'll order delivery.
Advisor: Any restaurant in mind?
Speaker: Not yet, I need to check what's available on DoorDash first.

Correct extraction:
- Topology: SEQUENTIAL chain (goal → order → find restaurant)
- Nodes: (1) "eat sushi tonight" [sp=0.5], (2) "order sushi delivery" [sp=0.6], \
(3) "find sushi restaurant on DoorDash" [sp=0.7]
- Edges: (1)-[decomposes_to]->(2): eating decomposes into ordering; \
(2)-[decomposes_to]->(3): ordering requires finding a restaurant
- End goal: int_001 "eat sushi tonight" — most abstract, everything else serves this

### Example B — Branching with alternatives

Dialogue:
Speaker: I've been thinking about getting into data science. I already took that Python course.
Advisor: What's next?
Speaker: I'm torn — I could either do a bootcamp or try to get an analyst role first. \
If I go bootcamp I'd need to save up money first.

Correct extraction:
- Topology: MIXED — branching alternatives with a prerequisite
- Nodes: (1) "transition into data science" [sp=0.4], (2) "completed Python course" [status=completed, sp=0.8], \
(3) "attend data science bootcamp" [sp=0.6], (4) "get entry-level analyst role" [sp=0.5], \
(5) "save money for bootcamp" [sp=0.5]
- Edges: (3)-[alternative]->(4): "either...or" = mutually exclusive; \
(5)-[enables]->(3): "need to save up money first" = prerequisite; \
(2)-[enables]->(1): completed course enables career transition
- End goal: int_001 "transition into data science"

### Example C — Fan-out alternatives (relationship repair)

Dialogue:
Speaker: Things have been tense with my partner since that argument. I want to make things right.
Advisor: What are you thinking?
Speaker: I'm not sure. Part of me thinks I should sit down and talk honestly about feelings. \
But another part thinks we need space first. And if talking goes well, \
maybe we could plan something special together.

Correct extraction:
- Topology: FAN-OUT from root, with sequential follow-up
- Nodes: (1) "repair relationship after argument" [sp=0.4], \
(2) "have honest conversation about feelings" [sp=0.6], \
(3) "give each other space first" [sp=0.5], \
(4) "plan something meaningful together" [sp=0.6]
- Edges: (1)-[alternative]->(2): "part of me thinks I should..." = option A; \
(1)-[alternative]->(3): "another part thinks..." = option B (mutually exclusive with (2)); \
(2)-[next_step]->(4): "if talking goes well, plan something" = temporal follow-up
- End goal: int_001 "repair relationship"
- CRITICAL: (2) and (3) are ALTERNATIVES, not decompositions. "Part of me... another part" \
signals mutually exclusive options. Use "alternative" when the speaker is choosing between \
approaches. Use "decomposes_to" only when sub-tasks are ALL needed (not either/or).

### Contrastive Examples — WRONG vs RIGHT

Wrong: save_money --[next_step]--> apply_bootcamp
Right: save_money --[enables]--> apply_bootcamp
Why: "I need to save up first" + "then I CAN apply" = prerequisite (enables), not mere sequence. \
Use "enables" when B DEPENDS on A. Use "next_step" only for temporal order WITHOUT dependency.

Wrong: talk_to_partner --[enables]--> give_space (treating two options as a chain)
Right: repair_relationship --[alternative]--> talk_to_partner, \
repair_relationship --[alternative]--> give_space
Why: "I could X or Y" means both are mutually exclusive options. \
Use "alternative" for either/or choices, not "decomposes_to" (which implies ALL sub-tasks are needed).

Wrong: buy_laptop --[decomposes_to]--> compare_options --[decomposes_to]--> check_reviews
Right: buy_laptop --[decomposes_to]--> compare_options, compare_options --[next_step]--> check_reviews
Why: Comparing and reviewing are at similar specificity — reviews follow comparison \
as a sequential step, not a further decomposition. "decomposes_to" requires parent→child \
(abstract→concrete) relationship.

### Common Mistakes:
- OVER-GENERATING NODES: Only extract intentions the speaker explicitly states or strongly implies. \
Aim for 3-5 nodes for a typical short conversation. Do NOT create nodes for minor details, \
intermediate steps the speaker doesn't mention, or the advisor's suggestions. \
Ask: "Did the speaker actually EXPRESS this intention?" If not, don't include it.
- LINEARIZING BRANCHES: When a speaker presents options ("either X or Y", "part of me... another part..."), \
these are fan-out alternatives, NOT sequential steps. Connect them to the parent goal.
- CONFUSING enables vs next_step: "enables" = B depends on A (prerequisite). \
"next_step" = A happens before B but B doesn't require A.
- CONFUSING decomposes_to vs next_step: "decomposes_to" = parent→child (abstract→concrete). \
"next_step" = temporal sequence between peers at similar abstraction.
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
        """Extract intention nodes and transitions from dialogue text (joint extraction)."""
        graph_data = self._extract_graph(text, speaker_label, domain)

        nodes = graph_data.get("nodes", [])
        transitions_data = graph_data.get("transitions", [])
        detected_domain = graph_data.get("domain", domain or "general")

        # Override domain if hint provided
        if domain:
            detected_domain = domain

        # Build action nodes
        action_nodes = [
            ActionNode(
                id=n["id"],
                text=n["text"],
                domain=detected_domain,
                source="expressed",
                status=n.get("status", "pending"),
                confidence=_clamp(n.get("confidence", 0.7)),
                specificity=_clamp(n.get("specificity", 0.5)),
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

        # Validate and build transitions
        node_ids = {n["id"] for n in nodes}
        valid_relations = {"next_step", "decomposes_to", "alternative", "enables", "evolves_to"}
        transitions = []
        for t in transitions_data:
            from_id = t.get("from_id", "")
            to_id = t.get("to_id", "")
            relation = t.get("relation", "next_step")
            # Skip invalid edges
            if from_id not in node_ids or to_id not in node_ids:
                continue
            if from_id == to_id:
                continue
            if relation not in valid_relations:
                relation = "next_step"
            transitions.append(
                Transition(
                    from_id=from_id,
                    to_id=to_id,
                    base_probability=_clamp(t.get("base_probability", 0.5)),
                    dna_adjusted_probability=_clamp(t.get("base_probability", 0.5)),
                    relation=relation,
                    confidence=_clamp(t.get("confidence", 0.5)),
                )
            )

        # Deduplicate edges (keep highest confidence)
        seen: dict[tuple[str, str], Transition] = {}
        for t in transitions:
            key = (t.from_id, t.to_id)
            if key not in seen or t.confidence > seen[key].confidence:
                seen[key] = t
        transitions = list(seen.values())

        # Resolve end goal
        end_goal = graph_data.get("end_goal") or graph_data.get("inferred_end_goal")
        if end_goal and end_goal not in node_ids:
            end_goal = _fallback_end_goal(nodes)

        return IntentionGraph(
            nodes=action_nodes,
            transitions=transitions,
            end_goal=end_goal,
            summary=f"Extracted {len(action_nodes)} intentions from {speaker_label}'s dialogue.",
        )

    def _extract_graph(self, text: str, speaker_label: str, domain: str) -> dict:
        """Joint extraction: nodes + transitions + end goal in one LLM call."""
        domain_hint = f"\nDomain hint: {domain}" if domain else ""
        user_message = (
            f"## Conversation Transcript\n\n{text}\n\n"
            f"## Target Speaker\n\nExtract the complete intention graph for "
            f"speaker labeled '{speaker_label}'.{domain_hint}\n"
            f"{_FEW_SHOT_EXAMPLES}"
        )
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            temperature=0.0,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text
        return _parse_graph_response(raw)


def _fallback_end_goal(nodes: list[dict]) -> str | None:
    """Pick the most abstract node (lowest specificity) as end goal fallback."""
    if not nodes:
        return None
    return min(nodes, key=lambda n: n.get("specificity", 0.5))["id"]


def _parse_graph_response(raw: str) -> dict:
    """Parse LLM response for joint graph extraction."""
    raw = _strip_markdown_fences(raw)

    # Try direct parse
    for candidate in [raw, _extract_outermost_json(raw)]:
        if not candidate:
            continue
        try:
            data = json.loads(candidate)
            if isinstance(data, dict) and "nodes" in data:
                return data
        except json.JSONDecodeError:
            continue

    # Fallback: try to repair truncated JSON
    repaired = _repair_truncated_json(raw)
    if repaired:
        try:
            data = json.loads(repaired)
            if isinstance(data, dict) and "nodes" in data:
                return data
        except json.JSONDecodeError:
            pass

    # Last resort: extract individual node objects via regex
    nodes = []
    for m in re.finditer(r'\{[^{}]*"id"\s*:\s*"int_\d+"[^{}]*\}', raw):
        try:
            obj = json.loads(m.group())
            if "text" in obj:
                nodes.append(obj)
        except json.JSONDecodeError:
            continue
    if nodes:
        return {"nodes": nodes, "transitions": [], "domain": "general"}

    return {"nodes": [], "transitions": [], "domain": "general"}


# Keep backward-compatible aliases for existing tests
_parse_nodes_response = _parse_graph_response


def _parse_transitions_response(raw: str) -> list[dict]:
    """Parse LLM response for transition inference (backward compat)."""
    raw = _strip_markdown_fences(raw)
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "transitions" in data:
            return data["transitions"]
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    objects = []
    for m in re.finditer(r'\{[^{}]*\}', raw):
        try:
            obj = json.loads(m.group())
            if "from_id" in obj and "to_id" in obj:
                objects.append(obj)
        except json.JSONDecodeError:
            continue
    return objects


def _extract_outermost_json(raw: str) -> str | None:
    """Extract the outermost JSON object from raw text."""
    start = raw.find("{")
    last = raw.rfind("}")
    if start != -1 and last != -1 and last > start:
        return raw[start:last + 1]
    return None


def _repair_truncated_json(raw: str) -> str | None:
    """Try to repair JSON truncated by max_tokens."""
    start = raw.find("{")
    if start == -1:
        return None
    fragment = raw[start:]
    opens = fragment.count("{") - fragment.count("}")
    open_brackets = fragment.count("[") - fragment.count("]")
    if opens <= 0 and open_brackets <= 0:
        return None
    fragment = re.sub(r',\s*"[^"]*"\s*:\s*$', '', fragment)
    fragment = re.sub(r',\s*$', '', fragment)
    fragment += "]" * max(0, open_brackets) + "}" * max(0, opens)
    return fragment


def _strip_markdown_fences(raw: str) -> str:
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return raw


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))
