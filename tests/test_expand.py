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
    assert len(expanded.nodes) > len(graph.nodes)
    inferred = [n for n in expanded.nodes if n.source == "inferred"]
    assert len(inferred) >= 1


def test_expand_preserves_original_nodes(expand: Expand):
    graph = _make_simple_graph()
    expanded = expand.run(graph)
    original_ids = {n.id for n in graph.nodes}
    expanded_ids = {n.id for n in expanded.nodes}
    assert original_ids.issubset(expanded_ids)
