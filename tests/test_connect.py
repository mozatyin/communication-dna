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
    assert len(graph.nodes) >= 2
    assert all(n.source == "expressed" for n in graph.nodes)
    assert all(n.domain != "" for n in graph.nodes)


def test_connect_identifies_key_intention(connect: Connect):
    graph = connect.run(
        text=SAMPLE_DIALOGUE,
        speaker_id="user_1",
        speaker_label="User",
    )
    assert graph.end_goal is not None
