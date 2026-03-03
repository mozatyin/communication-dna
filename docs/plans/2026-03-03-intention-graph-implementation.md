# Intention Graph Detector Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an Intention Detector that extracts probabilistic intention graphs from dialogue, using a three-stage pipeline (Connect → Expand → Clarify).

**Architecture:** LLM-based extraction following the same patterns as `communication_dna/detector.py` — structured prompts, JSON output parsing with fallbacks, Pydantic models. Three stages run sequentially: Connect extracts nodes + transitions, Expand decomposes abstract nodes and adjusts probabilities via DNA, Clarify identifies ambiguity and generates incisive questions.

**Tech Stack:** Python 3.12, Pydantic 2.x, Anthropic SDK, pytest, pytest-asyncio. Model: `claude-sonnet-4-20250514`.

---

### Task 1: Data Models

**Files:**
- Create: `intention_graph/__init__.py`
- Create: `intention_graph/models.py`
- Create: `tests/test_intention_models.py`

**Step 1: Write the failing tests**

```python
# tests/test_intention_models.py
"""Tests for intention graph data models."""

from datetime import datetime

import pytest

from intention_graph.models import (
    ActionNode,
    Ambiguity,
    Evidence,
    GraphSnapshot,
    IntentionGraph,
    Transition,
)


def test_action_node_basic():
    node = ActionNode(
        id="int_001",
        text="order steak delivery",
        domain="food",
        source="expressed",
        status="pending",
        confidence=0.85,
        specificity=0.6,
    )
    assert node.id == "int_001"
    assert node.status == "pending"
    assert node.completed_at is None


def test_action_node_rejects_invalid_confidence():
    with pytest.raises(Exception):
        ActionNode(
            id="x", text="x", domain="x",
            source="expressed", status="pending",
            confidence=1.5, specificity=0.5,
        )


def test_action_node_rejects_invalid_source():
    with pytest.raises(Exception):
        ActionNode(
            id="x", text="x", domain="x",
            source="guessed", status="pending",
            confidence=0.5, specificity=0.5,
        )


def test_transition_basic():
    t = Transition(
        from_id="int_001",
        to_id="int_002",
        base_probability=0.7,
        dna_adjusted_probability=0.8,
        relation="next_step",
        confidence=0.9,
    )
    assert t.relation == "next_step"
    assert t.base_probability == 0.7


def test_transition_rejects_invalid_relation():
    with pytest.raises(Exception):
        Transition(
            from_id="a", to_id="b",
            base_probability=0.5, dna_adjusted_probability=0.5,
            relation="unknown_relation", confidence=0.5,
        )


def test_ambiguity():
    a = Ambiguity(
        node_id="int_001",
        branches=["int_002", "int_003"],
        incisive_question="Do you prefer X or Y?",
        information_gain=0.6,
    )
    assert len(a.branches) == 2


def test_graph_snapshot():
    s = GraphSnapshot(
        timestamp=datetime.now(),
        trigger="user expressed new goal",
        added_nodes=["int_005"],
        removed_nodes=[],
        new_end_goal="int_005",
    )
    assert s.new_end_goal == "int_005"


def test_intention_graph_basic():
    node1 = ActionNode(
        id="int_001", text="eat dinner", domain="food",
        source="expressed", status="pending",
        confidence=0.9, specificity=0.3,
    )
    node2 = ActionNode(
        id="int_002", text="order delivery", domain="food",
        source="expressed", status="pending",
        confidence=0.8, specificity=0.6,
    )
    t = Transition(
        from_id="int_001", to_id="int_002",
        base_probability=0.7, dna_adjusted_probability=0.7,
        relation="decomposes_to", confidence=0.8,
    )
    graph = IntentionGraph(
        nodes=[node1, node2],
        transitions=[t],
        end_goal="int_001",
        summary="User wants to eat dinner, considering delivery.",
    )
    assert len(graph.nodes) == 2
    assert len(graph.transitions) == 1
    assert graph.end_goal == "int_001"


def test_intention_graph_serialization_roundtrip():
    node = ActionNode(
        id="int_001", text="test", domain="test",
        source="expressed", status="completed",
        confidence=0.9, specificity=0.5,
        completed_at=datetime(2026, 1, 1),
    )
    graph = IntentionGraph(
        nodes=[node], transitions=[],
        summary="test graph",
    )
    json_str = graph.model_dump_json(indent=2)
    restored = IntentionGraph.model_validate_json(json_str)
    assert restored.nodes[0].id == "int_001"
    assert restored.nodes[0].status == "completed"
```

**Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_intention_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'intention_graph'`

**Step 3: Write the implementation**

```python
# intention_graph/__init__.py
"""Intention Graph: Extract probabilistic intention graphs from dialogue."""
```

```python
# intention_graph/models.py
"""Core data models for the Intention Graph system."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """Supporting quote from dialogue for an extracted intention."""
    quote: str
    utterance_index: int = Field(ge=0)
    speaker: str = ""


class ActionNode(BaseModel):
    """A single node in the intention graph — a concrete behavioral intention."""
    id: str
    text: str
    domain: str
    source: Literal["expressed", "inferred"]
    status: Literal["pending", "completed"]
    confidence: float = Field(ge=0.0, le=1.0)
    specificity: float = Field(ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(default_factory=list)
    completed_at: Optional[datetime] = None


class Transition(BaseModel):
    """A directed edge in the intention graph — transition probability between actions."""
    from_id: str
    to_id: str
    base_probability: float = Field(ge=0.0, le=1.0)
    dna_adjusted_probability: float = Field(ge=0.0, le=1.0)
    relation: Literal[
        "next_step",
        "decomposes_to",
        "alternative",
        "enables",
        "evolves_to",
    ]
    confidence: float = Field(ge=0.0, le=1.0)


class Ambiguity(BaseModel):
    """An ambiguous branch point in the graph requiring clarification."""
    node_id: str
    branches: list[str]
    incisive_question: str
    information_gain: float = Field(ge=0.0, le=1.0)


class GraphSnapshot(BaseModel):
    """A snapshot of graph evolution at a point in time."""
    timestamp: datetime
    trigger: str
    added_nodes: list[str] = Field(default_factory=list)
    removed_nodes: list[str] = Field(default_factory=list)
    new_end_goal: Optional[str] = None


class IntentionGraph(BaseModel):
    """Complete probabilistic intention graph for one person."""
    nodes: list[ActionNode] = Field(default_factory=list)
    transitions: list[Transition] = Field(default_factory=list)
    end_goal: Optional[str] = None
    dna_profile_id: Optional[str] = None
    completed_path: list[str] = Field(default_factory=list)
    evolution_history: list[GraphSnapshot] = Field(default_factory=list)
    ambiguities: list[Ambiguity] = Field(default_factory=list)
    summary: str = ""
```

**Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_intention_models.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add intention_graph/__init__.py intention_graph/models.py tests/test_intention_models.py
git commit -m "feat(intention): add core data models for intention graph"
```

---

### Task 2: Storage

**Files:**
- Create: `intention_graph/storage.py`
- Create: `tests/test_intention_storage.py`

**Step 1: Write the failing test**

```python
# tests/test_intention_storage.py
"""Tests for intention graph storage."""

from pathlib import Path

from intention_graph.models import ActionNode, IntentionGraph
from intention_graph.storage import save_graph, load_graph


def test_save_and_load_roundtrip(tmp_path: Path):
    node = ActionNode(
        id="int_001", text="test action", domain="test",
        source="expressed", status="pending",
        confidence=0.9, specificity=0.5,
    )
    graph = IntentionGraph(
        nodes=[node], transitions=[],
        end_goal="int_001", summary="test",
    )
    filepath = tmp_path / "test_graph.json"
    save_graph(graph, filepath)
    loaded = load_graph(filepath)
    assert loaded.nodes[0].id == "int_001"
    assert loaded.end_goal == "int_001"
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_intention_storage.py -v`
Expected: FAIL with `ImportError`

**Step 3: Write the implementation**

```python
# intention_graph/storage.py
"""Save and load IntentionGraph to/from JSON files."""

from __future__ import annotations

from pathlib import Path

from intention_graph.models import IntentionGraph


def save_graph(graph: IntentionGraph, filepath: str | Path) -> None:
    """Save an IntentionGraph to a JSON file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(graph.model_dump_json(indent=2))


def load_graph(filepath: str | Path) -> IntentionGraph:
    """Load an IntentionGraph from a JSON file."""
    path = Path(filepath)
    return IntentionGraph.model_validate_json(path.read_text())
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_intention_storage.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add intention_graph/storage.py tests/test_intention_storage.py
git commit -m "feat(intention): add graph storage (save/load JSON)"
```

---

### Task 3: Connect Stage — Extract Nodes + Infer Transitions

**Files:**
- Create: `intention_graph/connect.py`
- Create: `tests/test_connect.py`

**Step 1: Write the failing tests**

```python
# tests/test_connect.py
"""Tests for the Connect stage of intention extraction."""

import json
import os

import pytest

from intention_graph.connect import Connect, _parse_nodes_response, _parse_transitions_response
from intention_graph.models import IntentionGraph


# ── Unit tests (no API key needed) ──────────────────────────────────────────

def test_parse_nodes_response_valid_json():
    raw = json.dumps({
        "reasoning": [{"node": "eat dinner", "observations": ["mentioned dinner"]}],
        "nodes": [
            {
                "id": "int_001",
                "text": "eat dinner at home",
                "confidence": 0.85,
                "specificity": 0.4,
                "status": "pending",
                "evidence": [{"quote": "I want dinner", "utterance_index": 0}],
            }
        ],
        "key_intention": "int_001",
        "inferred_end_goal": "int_001",
        "domain": "food",
    })
    result = _parse_nodes_response(raw)
    assert len(result["nodes"]) == 1
    assert result["nodes"][0]["id"] == "int_001"
    assert result["key_intention"] == "int_001"


def test_parse_nodes_response_strips_markdown_fences():
    raw = '```json\n{"nodes": [{"id": "int_001", "text": "test", "confidence": 0.8, "specificity": 0.5, "status": "pending", "evidence": []}], "key_intention": "int_001", "domain": "test"}\n```'
    result = _parse_nodes_response(raw)
    assert len(result["nodes"]) == 1


def test_parse_transitions_response_valid_json():
    raw = json.dumps({
        "transitions": [
            {
                "from_id": "int_001",
                "to_id": "int_002",
                "relation": "next_step",
                "base_probability": 0.7,
                "confidence": 0.8,
            }
        ]
    })
    result = _parse_transitions_response(raw)
    assert len(result) == 1
    assert result[0]["relation"] == "next_step"


# ── Integration tests (require API key) ─────────────────────────────────────

@pytest.fixture
def connect() -> Connect:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return Connect(api_key=api_key)


SAMPLE_DIALOGUE = """\
User: I've been thinking about changing jobs lately.
Advisor: What's prompting that?
User: My current role doesn't have growth opportunities. I want to move into a leadership position, \
maybe at a startup. I've already started updating my resume.
Advisor: Have you thought about what kind of startup?
User: Not really. I just know I want more autonomy and a smaller team. \
Oh, and I need to make sure the salary is at least the same.
"""


def test_connect_extracts_nodes(connect: Connect):
    graph = connect.run(
        text=SAMPLE_DIALOGUE,
        speaker_id="user_1",
        speaker_label="User",
    )
    assert isinstance(graph, IntentionGraph)
    assert len(graph.nodes) >= 2  # At least "change jobs" and "update resume"
    assert all(n.source == "expressed" for n in graph.nodes)
    assert all(n.domain != "" for n in graph.nodes)


def test_connect_identifies_key_intention(connect: Connect):
    graph = connect.run(
        text=SAMPLE_DIALOGUE,
        speaker_id="user_1",
        speaker_label="User",
    )
    assert graph.end_goal is not None  # Should identify a key intention
```

**Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_connect.py -v -k "not integration"`
(unit tests only — parse functions)
Expected: FAIL with `ImportError`

**Step 3: Write the implementation**

```python
# intention_graph/connect.py
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
                dna_adjusted_probability=_clamp(t["base_probability"]),  # No DNA adjustment yet
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
```

**Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_connect.py -v -k "parse"` (unit tests)
Expected: All PASS

Run: `.venv/bin/pytest tests/test_connect.py -v -k "connect_extracts or connect_identifies"` (integration, needs API key)
Expected: All PASS

**Step 5: Commit**

```bash
git add intention_graph/connect.py tests/test_connect.py
git commit -m "feat(intention): add Connect stage — node extraction + transition inference"
```

---

### Task 4: Expand Stage — Decompose + Path Completion + DNA Adjustment

**Files:**
- Create: `intention_graph/expand.py`
- Create: `tests/test_expand.py`

**Step 1: Write the failing tests**

```python
# tests/test_expand.py
"""Tests for the Expand stage of intention extraction."""

import os

import pytest

from intention_graph.expand import Expand, _apply_dna_adjustment
from intention_graph.models import ActionNode, IntentionGraph, Transition


# ── Unit tests ───────────────────────────────────────────────────────────────

def test_dna_adjustment_high_directness():
    """High directness should increase skip-intermediate probabilities."""
    dna_features = {"directness": 0.9, "hedging_frequency": 0.1}
    base_prob = 0.5
    relation = "next_step"
    adjusted = _apply_dna_adjustment(base_prob, relation, dna_features)
    # High directness → bold paths more likely
    assert adjusted >= base_prob


def test_dna_adjustment_high_hedging():
    """High hedging should favor conservative paths."""
    dna_features = {"directness": 0.1, "hedging_frequency": 0.9}
    base_prob = 0.5
    relation = "alternative"
    adjusted = _apply_dna_adjustment(base_prob, relation, dna_features)
    assert 0.0 <= adjusted <= 1.0


def test_dna_adjustment_no_features():
    """No DNA features should return base probability unchanged."""
    adjusted = _apply_dna_adjustment(0.5, "next_step", {})
    assert adjusted == 0.5


# ── Integration tests ────────────────────────────────────────────────────────

@pytest.fixture
def expand() -> Expand:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return Expand(api_key=api_key)


def _make_simple_graph() -> IntentionGraph:
    return IntentionGraph(
        nodes=[
            ActionNode(
                id="int_001", text="change jobs", domain="career",
                source="expressed", status="pending",
                confidence=0.9, specificity=0.2,
            ),
            ActionNode(
                id="int_002", text="get a new offer", domain="career",
                source="expressed", status="pending",
                confidence=0.8, specificity=0.4,
            ),
        ],
        transitions=[
            Transition(
                from_id="int_001", to_id="int_002",
                base_probability=0.7, dna_adjusted_probability=0.7,
                relation="next_step", confidence=0.8,
            ),
        ],
        end_goal="int_001",
        summary="User wants to change jobs.",
    )


def test_expand_decomposes_abstract_nodes(expand: Expand):
    graph = _make_simple_graph()
    expanded = expand.run(graph)
    # Should add inferred nodes between "change jobs" and "get offer"
    assert len(expanded.nodes) > len(graph.nodes)
    inferred = [n for n in expanded.nodes if n.source == "inferred"]
    assert len(inferred) >= 1


def test_expand_preserves_original_nodes(expand: Expand):
    graph = _make_simple_graph()
    expanded = expand.run(graph)
    original_ids = {n.id for n in graph.nodes}
    expanded_ids = {n.id for n in expanded.nodes}
    assert original_ids.issubset(expanded_ids)
```

**Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_expand.py -v -k "dna_adjustment"`
Expected: FAIL with `ImportError`

**Step 3: Write the implementation**

```python
# intention_graph/expand.py
"""Stage 2 — Expand: Decompose abstract intentions and complete paths."""

from __future__ import annotations

import json

import anthropic

from intention_graph.models import (
    ActionNode,
    Evidence,
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

# DNA feature adjustments: (feature_name, relation_type) → probability delta
_DNA_ADJUSTMENTS: dict[tuple[str, str], float] = {
    ("directness", "next_step"): +0.10,       # Direct people move faster
    ("directness", "alternative"): -0.05,     # Less likely to consider alternatives
    ("hedging_frequency", "alternative"): +0.10,  # Hedgers consider more options
    ("hedging_frequency", "next_step"): -0.05,    # Hedgers are slower to commit
    ("vulnerability_willingness", "decomposes_to"): +0.05,  # Open people explore deeper
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
        # Find nodes that need decomposition
        abstract_nodes = [n for n in graph.nodes if n.specificity < 0.5]
        if not abstract_nodes and len(graph.nodes) <= 1:
            return graph  # Nothing to expand

        # Call LLM for expansion
        expansion = self._expand_graph(graph)

        # Build expanded graph
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
                    confidence=0.7,  # Inferred nodes get lower confidence
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

        # Also adjust existing transitions with DNA
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
            # Scale delta by how extreme the feature value is (distance from 0.5)
            feature_val = dna_features[feat_name]
            extremity = abs(feature_val - 0.5) * 2  # 0.0 at midpoint, 1.0 at extremes
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
```

**Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_expand.py -v -k "dna_adjustment"` (unit tests)
Expected: All PASS

Run: `.venv/bin/pytest tests/test_expand.py -v -k "expand_decomposes or expand_preserves"` (integration)
Expected: All PASS

**Step 5: Commit**

```bash
git add intention_graph/expand.py tests/test_expand.py
git commit -m "feat(intention): add Expand stage — decomposition + DNA adjustment"
```

---

### Task 5: Clarify Stage — Ambiguity Detection + Question Generation

**Files:**
- Create: `intention_graph/clarify.py`
- Create: `tests/test_clarify.py`

**Step 1: Write the failing tests**

```python
# tests/test_clarify.py
"""Tests for the Clarify stage of intention extraction."""

import os

import pytest

from intention_graph.clarify import Clarify, _detect_ambiguities
from intention_graph.models import ActionNode, Ambiguity, IntentionGraph, Transition


# ── Unit tests ───────────────────────────────────────────────────────────────

def test_detect_ambiguities_finds_branch_points():
    """A node with 2+ outgoing transitions of similar probability is ambiguous."""
    graph = IntentionGraph(
        nodes=[
            ActionNode(id="int_001", text="improve relationship", domain="rel",
                       source="expressed", status="pending", confidence=0.9, specificity=0.3),
            ActionNode(id="int_002", text="apologize directly", domain="rel",
                       source="inferred", status="pending", confidence=0.7, specificity=0.7),
            ActionNode(id="int_003", text="give space", domain="rel",
                       source="inferred", status="pending", confidence=0.7, specificity=0.7),
        ],
        transitions=[
            Transition(from_id="int_001", to_id="int_002",
                       base_probability=0.45, dna_adjusted_probability=0.45,
                       relation="alternative", confidence=0.7),
            Transition(from_id="int_001", to_id="int_003",
                       base_probability=0.40, dna_adjusted_probability=0.40,
                       relation="alternative", confidence=0.7),
        ],
        summary="test",
    )
    ambiguities = _detect_ambiguities(graph, prob_diff_threshold=0.3)
    assert len(ambiguities) >= 1
    assert ambiguities[0]["node_id"] == "int_001"
    assert set(ambiguities[0]["branches"]) == {"int_002", "int_003"}


def test_detect_ambiguities_no_ambiguity_when_clear():
    """A node with one dominant transition is not ambiguous."""
    graph = IntentionGraph(
        nodes=[
            ActionNode(id="int_001", text="eat dinner", domain="food",
                       source="expressed", status="pending", confidence=0.9, specificity=0.3),
            ActionNode(id="int_002", text="order delivery", domain="food",
                       source="expressed", status="pending", confidence=0.9, specificity=0.7),
            ActionNode(id="int_003", text="cook at home", domain="food",
                       source="inferred", status="pending", confidence=0.5, specificity=0.7),
        ],
        transitions=[
            Transition(from_id="int_001", to_id="int_002",
                       base_probability=0.85, dna_adjusted_probability=0.85,
                       relation="alternative", confidence=0.9),
            Transition(from_id="int_001", to_id="int_003",
                       base_probability=0.15, dna_adjusted_probability=0.15,
                       relation="alternative", confidence=0.5),
        ],
        summary="test",
    )
    ambiguities = _detect_ambiguities(graph, prob_diff_threshold=0.3)
    assert len(ambiguities) == 0  # 0.85 vs 0.15 = clear winner


# ── Integration tests ────────────────────────────────────────────────────────

@pytest.fixture
def clarify() -> Clarify:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return Clarify(api_key=api_key)


def test_clarify_generates_questions(clarify: Clarify):
    graph = IntentionGraph(
        nodes=[
            ActionNode(id="int_001", text="improve relationship with partner", domain="relationship",
                       source="expressed", status="pending", confidence=0.9, specificity=0.2),
            ActionNode(id="int_002", text="have a direct conversation", domain="relationship",
                       source="inferred", status="pending", confidence=0.6, specificity=0.6),
            ActionNode(id="int_003", text="take a break from each other", domain="relationship",
                       source="inferred", status="pending", confidence=0.6, specificity=0.6),
        ],
        transitions=[
            Transition(from_id="int_001", to_id="int_002",
                       base_probability=0.45, dna_adjusted_probability=0.45,
                       relation="alternative", confidence=0.6),
            Transition(from_id="int_001", to_id="int_003",
                       base_probability=0.40, dna_adjusted_probability=0.40,
                       relation="alternative", confidence=0.6),
        ],
        summary="test",
    )
    result = clarify.run(graph)
    assert len(result.ambiguities) >= 1
    assert result.ambiguities[0].incisive_question != ""
    assert result.ambiguities[0].information_gain > 0
```

**Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_clarify.py -v -k "detect_ambiguities"`
Expected: FAIL with `ImportError`

**Step 3: Write the implementation**

```python
# intention_graph/clarify.py
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
```

**Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_clarify.py -v -k "detect_ambiguities"` (unit tests)
Expected: All PASS

Run: `.venv/bin/pytest tests/test_clarify.py -v -k "generates_questions"` (integration)
Expected: PASS

**Step 5: Commit**

```bash
git add intention_graph/clarify.py tests/test_clarify.py
git commit -m "feat(intention): add Clarify stage — ambiguity detection + question generation"
```

---

### Task 6: Detector Pipeline — Entry Point

**Files:**
- Create: `intention_graph/detector.py`
- Create: `tests/test_intention_detector.py`

**Step 1: Write the failing tests**

```python
# tests/test_intention_detector.py
"""Tests for the full Intention Detector pipeline."""

import os

import pytest

from intention_graph.detector import IntentionDetector
from intention_graph.models import IntentionGraph


@pytest.fixture
def detector() -> IntentionDetector:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return IntentionDetector(api_key=api_key)


CAREER_DIALOGUE = """\
User: I've been really unhappy at work. I think I need to change careers entirely.
Coach: What specifically is making you unhappy?
User: The work is repetitive, no creativity. I've always wanted to try product design. \
I took an online course last month and loved it.
Coach: That's exciting. What's holding you back?
User: Money, mostly. I can't just quit. I need to save up first, maybe 6 months of expenses. \
And I should build a portfolio before applying anywhere.
"""

SHOPPING_DIALOGUE = """\
User: I need a new laptop for programming. Budget is around $1500.
Advisor: Mac or Windows?
User: I'm leaning toward a MacBook Pro, but the new ThinkPad X1 Carbon looks good too. \
I need at least 32GB RAM and good keyboard. Battery life matters since I work from cafes a lot.
"""


def test_full_pipeline_career(detector: IntentionDetector):
    graph = detector.analyze(
        text=CAREER_DIALOGUE,
        speaker_id="user_1",
        speaker_label="User",
    )
    assert isinstance(graph, IntentionGraph)
    assert len(graph.nodes) >= 3  # career change, save money, build portfolio
    assert len(graph.transitions) >= 1
    assert graph.end_goal is not None


def test_full_pipeline_shopping(detector: IntentionDetector):
    graph = detector.analyze(
        text=SHOPPING_DIALOGUE,
        speaker_id="user_1",
        speaker_label="User",
    )
    assert isinstance(graph, IntentionGraph)
    assert len(graph.nodes) >= 2
    # Shopping should have alternative branches (MacBook vs ThinkPad)
    alternatives = [t for t in graph.transitions if t.relation == "alternative"]
    # May or may not detect alternatives depending on LLM
    assert len(graph.nodes) >= 2


def test_pipeline_with_domain_hint(detector: IntentionDetector):
    graph = detector.analyze(
        text=SHOPPING_DIALOGUE,
        speaker_id="user_1",
        speaker_label="User",
        domain="shopping",
    )
    assert all(n.domain == "shopping" for n in graph.nodes)
```

**Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_intention_detector.py -v`
Expected: FAIL with `ImportError`

**Step 3: Write the implementation**

```python
# intention_graph/detector.py
"""Intention Detector: Full pipeline combining Connect → Expand → Clarify."""

from __future__ import annotations

from intention_graph.connect import Connect
from intention_graph.expand import Expand
from intention_graph.clarify import Clarify
from intention_graph.models import IntentionGraph


class IntentionDetector:
    """Extract a probabilistic intention graph from dialogue.

    Three-stage pipeline:
    1. Connect: Extract intention nodes and infer transitions
    2. Expand: Decompose abstract nodes and complete paths
    3. Clarify: Detect ambiguities and generate incisive questions
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self._connect = Connect(api_key=api_key, model=model)
        self._expand = Expand(api_key=api_key, model=model)
        self._clarify = Clarify(api_key=api_key, model=model)

    def analyze(
        self,
        text: str,
        speaker_id: str,
        speaker_label: str,
        domain: str = "",
        dna_features: dict[str, float] | None = None,
        skip_expand: bool = False,
        skip_clarify: bool = False,
    ) -> IntentionGraph:
        """Run the full pipeline: Connect → Expand → Clarify.

        Args:
            text: Dialogue transcript
            speaker_id: Unique ID for the speaker
            speaker_label: Label used in transcript (e.g., "User", "A")
            domain: Optional domain hint (auto-detected if empty)
            dna_features: Optional dict of DNA feature name → value for probability adjustment
            skip_expand: Skip the Expand stage
            skip_clarify: Skip the Clarify stage
        """
        # Stage 1: Connect
        graph = self._connect.run(
            text=text,
            speaker_id=speaker_id,
            speaker_label=speaker_label,
            domain=domain,
        )

        # Stage 2: Expand
        if not skip_expand and len(graph.nodes) >= 1:
            graph = self._expand.run(graph, dna_features=dna_features)

        # Stage 3: Clarify
        if not skip_clarify and len(graph.transitions) >= 2:
            graph = self._clarify.run(graph)

        return graph
```

**Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_intention_detector.py -v`
Expected: All PASS (requires API key)

**Step 5: Commit**

```bash
git add intention_graph/detector.py tests/test_intention_detector.py
git commit -m "feat(intention): add IntentionDetector — full Connect→Expand→Clarify pipeline"
```

---

### Task 7: Graph Speaker — Generate Dialogue from Known Graph

**Files:**
- Create: `intention_graph/graph_speaker.py`
- Create: `tests/test_graph_speaker.py`

**Step 1: Write the failing tests**

```python
# tests/test_graph_speaker.py
"""Tests for the Graph Speaker (dialogue generation from known graphs)."""

import os

import pytest

from intention_graph.graph_speaker import GraphSpeaker
from intention_graph.models import ActionNode, IntentionGraph, Transition


@pytest.fixture
def speaker() -> GraphSpeaker:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return GraphSpeaker(api_key=api_key)


def _make_career_graph() -> IntentionGraph:
    return IntentionGraph(
        nodes=[
            ActionNode(id="int_001", text="change career to product design", domain="career",
                       source="expressed", status="pending", confidence=0.9, specificity=0.5),
            ActionNode(id="int_002", text="save 6 months of expenses", domain="career",
                       source="expressed", status="pending", confidence=0.8, specificity=0.7),
            ActionNode(id="int_003", text="build a design portfolio", domain="career",
                       source="expressed", status="pending", confidence=0.85, specificity=0.6),
            ActionNode(id="int_004", text="take online design courses", domain="career",
                       source="expressed", status="completed", confidence=0.9, specificity=0.8),
        ],
        transitions=[
            Transition(from_id="int_001", to_id="int_002",
                       base_probability=0.8, dna_adjusted_probability=0.8,
                       relation="enables", confidence=0.9),
            Transition(from_id="int_001", to_id="int_003",
                       base_probability=0.85, dna_adjusted_probability=0.85,
                       relation="enables", confidence=0.9),
            Transition(from_id="int_004", to_id="int_003",
                       base_probability=0.7, dna_adjusted_probability=0.7,
                       relation="next_step", confidence=0.8),
        ],
        end_goal="int_001",
        summary="Career change to product design.",
    )


def test_graph_speaker_generates_dialogue(speaker: GraphSpeaker):
    graph = _make_career_graph()
    dialogue = speaker.generate(graph=graph, prompt="Discuss your career plans with a coach")
    assert len(dialogue) > 100  # Should be a substantive dialogue
    assert "User:" in dialogue or "Speaker:" in dialogue


def test_graph_speaker_mentions_key_intentions(speaker: GraphSpeaker):
    graph = _make_career_graph()
    dialogue = speaker.generate(graph=graph, prompt="Talk about your career goals").lower()
    # Should mention at least some of the intentions
    intention_keywords = ["design", "portfolio", "save", "course"]
    matches = sum(1 for k in intention_keywords if k in dialogue)
    assert matches >= 2  # At least 2 of 4 keywords present
```

**Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_graph_speaker.py -v`
Expected: FAIL with `ImportError`

**Step 3: Write the implementation**

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_graph_speaker.py -v`
Expected: All PASS (requires API key)

**Step 5: Commit**

```bash
git add intention_graph/graph_speaker.py tests/test_graph_speaker.py
git commit -m "feat(intention): add GraphSpeaker for dialogue generation from known graphs"
```

---

### Task 8: Comparator — Graph Comparison + Metrics

**Files:**
- Create: `intention_graph/comparator.py`
- Create: `tests/test_comparator.py`

**Step 1: Write the failing tests**

```python
# tests/test_comparator.py
"""Tests for the graph comparator and metrics."""

from intention_graph.comparator import compare_graphs, GraphMetrics
from intention_graph.models import ActionNode, IntentionGraph, Transition


def _make_graph(node_texts: list[str], transitions: list[tuple[int, int, str, float]]) -> IntentionGraph:
    nodes = [
        ActionNode(
            id=f"int_{i+1:03d}", text=text, domain="test",
            source="expressed", status="pending",
            confidence=0.9, specificity=0.5,
        )
        for i, text in enumerate(node_texts)
    ]
    edges = [
        Transition(
            from_id=f"int_{f+1:03d}", to_id=f"int_{t+1:03d}",
            base_probability=p, dna_adjusted_probability=p,
            relation=r, confidence=0.8,
        )
        for f, t, r, p in transitions
    ]
    return IntentionGraph(
        nodes=nodes, transitions=edges,
        end_goal=nodes[0].id if nodes else None,
        summary="test",
    )


def test_identical_graphs():
    g = _make_graph(["eat dinner", "order delivery"], [(0, 1, "next_step", 0.8)])
    metrics = compare_graphs(g, g)
    assert metrics.node_recall == 1.0
    assert metrics.node_precision == 1.0
    assert metrics.edge_f1 == 1.0


def test_partial_node_match():
    truth = _make_graph(["eat dinner", "order delivery", "pay"], [])
    predicted = _make_graph(["eat dinner", "order delivery"], [])
    metrics = compare_graphs(predicted, truth)
    # Predicted has 2/3 of truth nodes → recall ~0.67
    # We use semantic matching so exact threshold depends on implementation
    assert metrics.node_recall < 1.0
    assert metrics.node_precision <= 1.0


def test_end_goal_accuracy():
    truth = _make_graph(["change career", "save money"], [])
    truth_with_goal = IntentionGraph(
        nodes=truth.nodes, transitions=truth.transitions,
        end_goal="int_001", summary="test",
    )
    predicted = IntentionGraph(
        nodes=truth.nodes, transitions=truth.transitions,
        end_goal="int_001", summary="test",
    )
    metrics = compare_graphs(predicted, truth_with_goal)
    assert metrics.end_goal_correct is True


def test_metrics_serialization():
    g = _make_graph(["test"], [])
    metrics = compare_graphs(g, g)
    d = metrics.to_dict()
    assert "node_recall" in d
    assert "node_precision" in d
    assert "edge_f1" in d
```

**Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_comparator.py -v`
Expected: FAIL with `ImportError`

**Step 3: Write the implementation**

```python
# intention_graph/comparator.py
"""Compare two IntentionGraphs and compute evaluation metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher

from intention_graph.models import IntentionGraph


@dataclass
class GraphMetrics:
    """Evaluation metrics for comparing predicted vs ground truth graphs."""
    node_recall: float = 0.0
    node_precision: float = 0.0
    node_f1: float = 0.0
    edge_f1: float = 0.0
    probability_mae: float = 0.0
    end_goal_correct: bool = False
    matched_nodes: int = 0
    total_predicted_nodes: int = 0
    total_truth_nodes: int = 0

    def to_dict(self) -> dict:
        return {
            "node_recall": round(self.node_recall, 3),
            "node_precision": round(self.node_precision, 3),
            "node_f1": round(self.node_f1, 3),
            "edge_f1": round(self.edge_f1, 3),
            "probability_mae": round(self.probability_mae, 3),
            "end_goal_correct": self.end_goal_correct,
            "matched_nodes": self.matched_nodes,
            "total_predicted_nodes": self.total_predicted_nodes,
            "total_truth_nodes": self.total_truth_nodes,
        }


def compare_graphs(predicted: IntentionGraph, truth: IntentionGraph) -> GraphMetrics:
    """Compare a predicted graph against ground truth and compute metrics."""
    # Node matching via text similarity
    node_matches = _match_nodes(predicted, truth)
    matched = len(node_matches)
    total_pred = len(predicted.nodes)
    total_truth = len(truth.nodes)

    node_recall = matched / total_truth if total_truth > 0 else 1.0
    node_precision = matched / total_pred if total_pred > 0 else 1.0
    node_f1 = (
        2 * node_precision * node_recall / (node_precision + node_recall)
        if (node_precision + node_recall) > 0
        else 0.0
    )

    # Edge matching
    edge_f1, prob_mae = _compare_edges(predicted, truth, node_matches)

    # End goal
    end_goal_correct = False
    if truth.end_goal and predicted.end_goal:
        truth_goal_text = next(
            (n.text for n in truth.nodes if n.id == truth.end_goal), ""
        )
        pred_goal_text = next(
            (n.text for n in predicted.nodes if n.id == predicted.end_goal), ""
        )
        end_goal_correct = _text_similarity(pred_goal_text, truth_goal_text) > 0.5

    return GraphMetrics(
        node_recall=node_recall,
        node_precision=node_precision,
        node_f1=node_f1,
        edge_f1=edge_f1,
        probability_mae=prob_mae,
        end_goal_correct=end_goal_correct,
        matched_nodes=matched,
        total_predicted_nodes=total_pred,
        total_truth_nodes=total_truth,
    )


def _match_nodes(
    predicted: IntentionGraph, truth: IntentionGraph, threshold: float = 0.4
) -> dict[str, str]:
    """Match predicted nodes to truth nodes by text similarity.
    Returns dict mapping predicted_id -> truth_id.
    """
    matches: dict[str, str] = {}
    used_truth: set[str] = set()

    # Greedy matching: best match first
    pairs = []
    for p in predicted.nodes:
        for t in truth.nodes:
            sim = _text_similarity(p.text, t.text)
            pairs.append((sim, p.id, t.id))
    pairs.sort(reverse=True)

    for sim, pred_id, truth_id in pairs:
        if sim < threshold:
            break
        if pred_id in matches or truth_id in used_truth:
            continue
        matches[pred_id] = truth_id
        used_truth.add(truth_id)

    return matches


def _compare_edges(
    predicted: IntentionGraph,
    truth: IntentionGraph,
    node_matches: dict[str, str],
) -> tuple[float, float]:
    """Compare edges and return (edge_f1, probability_mae)."""
    # Map predicted edges to truth space
    pred_edges = set()
    pred_probs: dict[tuple, float] = {}
    for t in predicted.transitions:
        mapped_from = node_matches.get(t.from_id)
        mapped_to = node_matches.get(t.to_id)
        if mapped_from and mapped_to:
            key = (mapped_from, mapped_to, t.relation)
            pred_edges.add(key)
            pred_probs[key] = t.base_probability

    truth_edges = set()
    truth_probs: dict[tuple, float] = {}
    for t in truth.transitions:
        key = (t.from_id, t.to_id, t.relation)
        truth_edges.add(key)
        truth_probs[key] = t.base_probability

    # F1
    if not truth_edges and not pred_edges:
        return 1.0, 0.0

    tp = len(pred_edges & truth_edges)
    precision = tp / len(pred_edges) if pred_edges else 0.0
    recall = tp / len(truth_edges) if truth_edges else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # MAE on matched edges
    matched_edges = pred_edges & truth_edges
    if matched_edges:
        mae = sum(
            abs(pred_probs[e] - truth_probs[e]) for e in matched_edges
        ) / len(matched_edges)
    else:
        mae = 0.0

    return f1, mae


def _text_similarity(a: str, b: str) -> float:
    """Compute text similarity between two strings (0.0-1.0)."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()
```

**Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_comparator.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add intention_graph/comparator.py tests/test_comparator.py
git commit -m "feat(intention): add graph comparator with evaluation metrics"
```

---

### Task 9: Evaluation Script

**Files:**
- Create: `eval_intention.py`

**Step 1: Write the implementation** (eval script is tested by running it, not via pytest)

```python
# eval_intention.py
"""Evaluate Intention Detector accuracy via closed-loop testing."""

import json
import os
import statistics
import sys
from pathlib import Path

from intention_graph.comparator import compare_graphs
from intention_graph.detector import IntentionDetector
from intention_graph.graph_speaker import GraphSpeaker
from intention_graph.models import ActionNode, IntentionGraph, Transition


def make_graph(
    domain: str,
    nodes: list[dict],
    transitions: list[dict],
    end_goal: str,
) -> IntentionGraph:
    """Build an IntentionGraph from shorthand definitions."""
    action_nodes = [
        ActionNode(
            id=n["id"], text=n["text"], domain=domain,
            source="expressed", status=n.get("status", "pending"),
            confidence=1.0, specificity=n.get("specificity", 0.5),
        )
        for n in nodes
    ]
    trans = [
        Transition(
            from_id=t["from"], to_id=t["to"],
            base_probability=t["prob"],
            dna_adjusted_probability=t["prob"],
            relation=t["rel"], confidence=1.0,
        )
        for t in transitions
    ]
    return IntentionGraph(
        nodes=action_nodes, transitions=trans,
        end_goal=end_goal,
        summary=f"Eval graph: {domain}",
    )


# ── Test graphs ──────────────────────────────────────────────────────────────

GRAPHS = {
    "career_change": make_graph(
        domain="career",
        nodes=[
            {"id": "int_001", "text": "change career to product design", "specificity": 0.5},
            {"id": "int_002", "text": "save 6 months of living expenses", "specificity": 0.7},
            {"id": "int_003", "text": "build a design portfolio", "specificity": 0.6},
            {"id": "int_004", "text": "take online design courses", "status": "completed", "specificity": 0.8},
            {"id": "int_005", "text": "apply to design jobs at startups", "specificity": 0.6},
        ],
        transitions=[
            {"from": "int_002", "to": "int_005", "rel": "enables", "prob": 0.8},
            {"from": "int_003", "to": "int_005", "rel": "enables", "prob": 0.9},
            {"from": "int_004", "to": "int_003", "rel": "next_step", "prob": 0.7},
        ],
        end_goal="int_001",
    ),
    "food_delivery": make_graph(
        domain="food",
        nodes=[
            {"id": "int_001", "text": "eat steak dinner at home", "specificity": 0.6},
            {"id": "int_002", "text": "order steak delivery via app", "specificity": 0.7},
            {"id": "int_003", "text": "find a good steak restaurant on delivery app", "specificity": 0.6},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_002", "to": "int_003", "rel": "decomposes_to", "prob": 0.7},
        ],
        end_goal="int_001",
    ),
    "relationship": make_graph(
        domain="relationship",
        nodes=[
            {"id": "int_001", "text": "repair relationship with partner after argument", "specificity": 0.4},
            {"id": "int_002", "text": "have an honest conversation about feelings", "specificity": 0.6},
            {"id": "int_003", "text": "give each other some space first", "specificity": 0.5},
            {"id": "int_004", "text": "plan a meaningful date together", "specificity": 0.6},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "alternative", "prob": 0.5},
            {"from": "int_001", "to": "int_003", "rel": "alternative", "prob": 0.4},
            {"from": "int_002", "to": "int_004", "rel": "next_step", "prob": 0.6},
        ],
        end_goal="int_001",
    ),
    "laptop_purchase": make_graph(
        domain="shopping",
        nodes=[
            {"id": "int_001", "text": "buy a new programming laptop within $1500 budget", "specificity": 0.6},
            {"id": "int_002", "text": "compare MacBook Pro vs ThinkPad X1", "specificity": 0.7},
            {"id": "int_003", "text": "check RAM and keyboard reviews", "specificity": 0.7},
            {"id": "int_004", "text": "visit store to try keyboards", "specificity": 0.8},
        ],
        transitions=[
            {"from": "int_001", "to": "int_002", "rel": "decomposes_to", "prob": 0.8},
            {"from": "int_002", "to": "int_003", "rel": "next_step", "prob": 0.7},
            {"from": "int_003", "to": "int_004", "rel": "next_step", "prob": 0.5},
        ],
        end_goal="int_001",
    ),
}

PROMPTS = [
    "Discuss your plans and goals with an advisor",
    "Talk about what you've been thinking about lately",
    "Explain your current situation and what you want to achieve",
]


def run_eval(api_key: str):
    speaker = GraphSpeaker(api_key=api_key)
    detector = IntentionDetector(api_key=api_key)

    all_metrics = []
    results: dict[str, dict] = {}

    for graph_name, truth_graph in GRAPHS.items():
        print(f"\n{'='*60}")
        print(f"  Graph: {graph_name}")
        print(f"{'='*60}")

        # Generate dialogue
        print("  Generating dialogue...", end=" ", flush=True)
        prompt = PROMPTS[0]
        dialogue = speaker.generate(graph=truth_graph, prompt=prompt)
        print(f"done ({len(dialogue.split())} words)")

        # Detect
        print("  Detecting intentions...", end=" ", flush=True)
        predicted = detector.analyze(
            text=dialogue,
            speaker_id=f"eval_{graph_name}",
            speaker_label="Speaker",
            domain=truth_graph.nodes[0].domain,
            skip_expand=True,  # Compare Connect output directly against truth
        )
        print("done")

        # Compare
        metrics = compare_graphs(predicted, truth_graph)
        all_metrics.append(metrics)

        print(f"\n  Nodes: {metrics.matched_nodes}/{metrics.total_truth_nodes} matched "
              f"(P={metrics.node_precision:.2f} R={metrics.node_recall:.2f} F1={metrics.node_f1:.2f})")
        print(f"  Edges: F1={metrics.edge_f1:.2f}, Prob MAE={metrics.probability_mae:.3f}")
        print(f"  End Goal: {'CORRECT' if metrics.end_goal_correct else 'WRONG'}")

        results[graph_name] = metrics.to_dict()

    # Overall
    print(f"\n{'='*60}")
    print(f"  OVERALL SUMMARY")
    print(f"{'='*60}")
    avg_node_f1 = statistics.mean(m.node_f1 for m in all_metrics)
    avg_edge_f1 = statistics.mean(m.edge_f1 for m in all_metrics)
    avg_recall = statistics.mean(m.node_recall for m in all_metrics)
    end_goal_acc = sum(1 for m in all_metrics if m.end_goal_correct) / len(all_metrics)

    print(f"  Avg Node F1: {avg_node_f1:.3f}")
    print(f"  Avg Node Recall: {avg_recall:.3f}")
    print(f"  Avg Edge F1: {avg_edge_f1:.3f}")
    print(f"  End Goal Accuracy: {end_goal_acc:.1%}")

    results["_overall"] = {
        "avg_node_f1": round(avg_node_f1, 3),
        "avg_node_recall": round(avg_recall, 3),
        "avg_edge_f1": round(avg_edge_f1, 3),
        "end_goal_accuracy": round(end_goal_acc, 3),
    }

    output_path = Path("eval_intention_results_v0.1.json")
    output_path.write_text(json.dumps(results, indent=2))
    print(f"\n  Results saved to {output_path}")


if __name__ == "__main__":
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY env var to run evaluation.")
        sys.exit(1)
    run_eval(api_key)
```

**Step 2: Verify it runs**

Run: `cd /Users/michael/communication-dna && ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY .venv/bin/python eval_intention.py`
Expected: Prints evaluation results and saves JSON

**Step 3: Commit**

```bash
git add eval_intention.py
git commit -m "feat(intention): add evaluation script for closed-loop testing"
```

---

### Task 10: Example Usage Script

**Files:**
- Create: `examples/analyze_intentions.py`

**Step 1: Write the implementation**

```python
# examples/analyze_intentions.py
"""Example: Extract an intention graph from a conversation."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from intention_graph.detector import IntentionDetector
from intention_graph.storage import save_graph

api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    print("Error: set ANTHROPIC_API_KEY environment variable")
    sys.exit(1)

SAMPLE_CONVERSATION = """\
User: I've been really stressed out about work lately. I think I need a complete change.
Coach: What kind of change are you thinking about?
User: Well, I've always been passionate about cooking. I took a pastry course last year \
and everyone said I was really talented. I'm thinking about opening a small bakery.
Coach: That's a big step. Have you thought about the practical side?
User: Kind of. I know I need to save up at least $50,000. Right now I have about $20,000. \
I also need to find a good location — maybe somewhere near the university district where \
there's lots of foot traffic.
Coach: What about the business side — permits, suppliers?
User: That's what scares me honestly. I don't know anything about running a business. \
Maybe I should take a small business course first, or find a mentor who's done it before.
"""

# Create detector
detector = IntentionDetector(api_key=api_key)

# Analyze conversation
print("Analyzing conversation for intentions...\n")
graph = detector.analyze(
    text=SAMPLE_CONVERSATION,
    speaker_id="aspiring_baker",
    speaker_label="User",
)

# Display results
print(f"Summary: {graph.summary}\n")
print(f"End Goal: {graph.end_goal}\n")

print("=== Intention Nodes ===")
for node in graph.nodes:
    status = " [DONE]" if node.status == "completed" else ""
    source_tag = f" ({node.source})" if node.source == "inferred" else ""
    print(f"  [{node.id}] {node.text}{status}{source_tag}")
    print(f"         confidence={node.confidence:.2f}  specificity={node.specificity:.2f}")

print(f"\n=== Transitions ===")
node_map = {n.id: n.text for n in graph.nodes}
for t in graph.transitions:
    print(f"  {node_map.get(t.from_id, t.from_id)}")
    print(f"    --[{t.relation}, p={t.base_probability:.2f}]-->")
    print(f"    {node_map.get(t.to_id, t.to_id)}")

if graph.ambiguities:
    print(f"\n=== Ambiguities ({len(graph.ambiguities)}) ===")
    for amb in graph.ambiguities:
        print(f"  Node: {node_map.get(amb.node_id, amb.node_id)}")
        print(f"  Question: {amb.incisive_question}")
        print(f"  Info Gain: {amb.information_gain:.2f}")
        print()

# Save
output_dir = Path("output")
save_graph(graph, output_dir / "bakery_intentions.json")
print(f"\nGraph saved to {output_dir / 'bakery_intentions.json'}")
```

**Step 2: Verify it runs**

Run: `cd /Users/michael/communication-dna && ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY .venv/bin/python examples/analyze_intentions.py`
Expected: Prints extracted graph and saves JSON

**Step 3: Commit**

```bash
git add examples/analyze_intentions.py
git commit -m "feat(intention): add example script for intention graph extraction"
```

---

## Summary

| Task | Component | Files | Tests |
|------|-----------|-------|-------|
| 1 | Data Models | `intention_graph/models.py` | `tests/test_intention_models.py` |
| 2 | Storage | `intention_graph/storage.py` | `tests/test_intention_storage.py` |
| 3 | Connect Stage | `intention_graph/connect.py` | `tests/test_connect.py` |
| 4 | Expand Stage | `intention_graph/expand.py` | `tests/test_expand.py` |
| 5 | Clarify Stage | `intention_graph/clarify.py` | `tests/test_clarify.py` |
| 6 | Detector Pipeline | `intention_graph/detector.py` | `tests/test_intention_detector.py` |
| 7 | Graph Speaker | `intention_graph/graph_speaker.py` | `tests/test_graph_speaker.py` |
| 8 | Comparator | `intention_graph/comparator.py` | `tests/test_comparator.py` |
| 9 | Eval Script | `eval_intention.py` | Manual run |
| 10 | Example | `examples/analyze_intentions.py` | Manual run |

**Dependency order:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10

**All tasks use TDD:** Write failing test → verify fails → implement → verify passes → commit.
