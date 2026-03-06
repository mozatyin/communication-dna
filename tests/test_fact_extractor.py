"""Tests for V2.4 FactExtractor — fact, reality, secrets extraction."""

import json
from unittest.mock import MagicMock, patch

from super_brain.fact_extractor import FactExtractor, _parse_fact_response, _deduplicate_facts
from super_brain.models import Fact, FactExtractionResult


def test_parse_fact_response_valid_json():
    raw = json.dumps({
        "facts": [
            {"category": "career", "content": "software engineer", "confidence": 0.9},
            {"category": "hobby", "content": "plays guitar", "confidence": 0.7},
        ],
        "reality": {
            "summary": "An engineer who plays guitar",
            "domains": {"career": "software engineer"},
            "constraints": [],
            "resources": ["technical skills"],
        },
        "secrets": ["avoids discussing family"],
        "contradictions": [],
    })
    data = _parse_fact_response(raw)
    assert len(data["facts"]) == 2
    assert data["facts"][0]["category"] == "career"
    assert data["reality"]["summary"] == "An engineer who plays guitar"
    assert len(data["secrets"]) == 1


def test_parse_fact_response_code_block():
    raw = "```json\n" + json.dumps({
        "facts": [],
        "reality": None,
        "secrets": [],
        "contradictions": [],
    }) + "\n```"
    data = _parse_fact_response(raw)
    assert data["facts"] == []


def test_parse_fact_response_invalid():
    data = _parse_fact_response("not json at all")
    assert data["facts"] == []
    assert data["reality"] is None
    assert data["secrets"] == []
    assert data["contradictions"] == []


def test_deduplicate_facts_removes_duplicates():
    existing = [
        Fact(category="career", content="software engineer", confidence=0.9, source_turn=3),
    ]
    new_raw = [
        {"category": "career", "content": "software engineer", "confidence": 0.8},  # duplicate
        {"category": "hobby", "content": "plays guitar", "confidence": 0.7},        # new
    ]
    result = _deduplicate_facts(new_raw, existing, current_turn=6)
    assert len(result) == 1
    assert result[0].content == "plays guitar"
    assert result[0].source_turn == 6


def test_deduplicate_facts_case_insensitive():
    existing = [
        Fact(category="career", content="Software Engineer", confidence=0.9, source_turn=3),
    ]
    new_raw = [
        {"category": "career", "content": "software engineer", "confidence": 0.8},
    ]
    result = _deduplicate_facts(new_raw, existing, current_turn=6)
    assert len(result) == 0


def test_deduplicate_facts_empty_existing():
    new_raw = [
        {"category": "career", "content": "engineer", "confidence": 0.9},
    ]
    result = _deduplicate_facts(new_raw, [], current_turn=1)
    assert len(result) == 1
    assert result[0].source_turn == 1


def test_fact_extractor_extract_with_mock():
    """Test FactExtractor.extract() with a mocked LLM response."""
    with patch("super_brain.fact_extractor.anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "facts": [
                {"category": "career", "content": "data scientist", "confidence": 0.85},
            ],
            "reality": {
                "summary": "A data scientist exploring new opportunities",
                "domains": {"career": "data science"},
                "constraints": ["limited time"],
                "resources": ["analytical skills"],
            },
            "secrets": ["seems stressed about work"],
            "contradictions": [],
        }))]
        mock_client.messages.create.return_value = mock_response

        extractor = FactExtractor(api_key="test-key")
        conversation = [
            {"role": "chatter", "text": "What do you do for work?"},
            {"role": "speaker", "text": "I'm a data scientist, been doing it for three years."},
        ]
        result = extractor.extract(conversation, existing_facts=[], current_turn=2)

        assert isinstance(result, FactExtractionResult)
        assert len(result.new_facts) == 1
        assert result.new_facts[0].category == "career"
        assert result.new_facts[0].content == "data scientist"
        assert result.new_facts[0].source_turn == 2
        assert result.reality is not None
        assert result.reality.summary == "A data scientist exploring new opportunities"
        assert result.secrets == ["seems stressed about work"]

        # Verify the LLM was called
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs["max_tokens"] == 4096
