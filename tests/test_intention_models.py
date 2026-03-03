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
