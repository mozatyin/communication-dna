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
