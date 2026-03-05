"""Tests for LLM-based scenario scoring."""

import json
from unittest.mock import MagicMock, patch

import pytest

from assessment.scenario_scorer import ScenarioScorer


def _mock_response(score_json: dict) -> MagicMock:
    """Create a mock Anthropic response."""
    msg = MagicMock()
    msg.content = [MagicMock(text=json.dumps(score_json))]
    return msg


@pytest.fixture
def scorer():
    return ScenarioScorer(api_key="test-key")


def test_score_scenario_returns_structured_result(scorer):
    expected = {
        "dimension_relevance": 0.4,
        "depth_of_reasoning": 0.3,
        "practical_applicability": 0.5,
        "originality": 0.3,
        "total_score": 1.5,
        "feedback": "Good analysis of the chatbot problem."
    }
    with patch.object(scorer._client.messages, "create", return_value=_mock_response(expected)):
        result = scorer.score(
            question="Chatbot scenario question...",
            rubric={
                "dimension_relevance": "Does it question the 80% metric?",
                "depth_of_reasoning": "Does it propose experiments?",
                "practical_applicability": "Are experiments actionable?",
                "originality": "Non-obvious factors?",
            },
            response="The 80% metric is misleading because...",
            dimensions=["pdca_thinking", "critical_questioning"],
        )
    assert result["score"] == 1.5
    assert "feedback" in result
    assert "dimension_scores" in result


def test_score_clamps_to_max(scorer):
    inflated = {
        "dimension_relevance": 0.5,
        "depth_of_reasoning": 0.5,
        "practical_applicability": 0.5,
        "originality": 0.5,
        "total_score": 3.0,
        "feedback": "Excellent."
    }
    with patch.object(scorer._client.messages, "create", return_value=_mock_response(inflated)):
        result = scorer.score(
            question="Q", rubric={"a": "b"}, response="R", dimensions=["pdca_thinking"],
        )
    assert result["score"] <= 2.0


def test_score_handles_malformed_response(scorer):
    bad_msg = MagicMock()
    bad_msg.content = [MagicMock(text="This is not JSON")]
    with patch.object(scorer._client.messages, "create", return_value=bad_msg):
        result = scorer.score(
            question="Q", rubric={"a": "b"}, response="R", dimensions=["pdca_thinking"],
        )
    assert result["score"] == 0
