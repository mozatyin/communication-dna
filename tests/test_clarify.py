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
