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
