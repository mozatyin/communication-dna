# intention_graph/detector.py
"""Intention Detector: Full pipeline combining Connect -> Expand -> Clarify."""

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
        """Run the full pipeline: Connect -> Expand -> Clarify.

        Args:
            text: Dialogue transcript
            speaker_id: Unique ID for the speaker
            speaker_label: Label used in transcript (e.g., "User", "A")
            domain: Optional domain hint (auto-detected if empty)
            dna_features: Optional dict of DNA feature name -> value for probability adjustment
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
