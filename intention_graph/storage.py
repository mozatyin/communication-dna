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
