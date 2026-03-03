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
