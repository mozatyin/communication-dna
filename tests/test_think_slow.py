"""Tests for V2.1 Think Slow periodic extraction."""

from unittest.mock import MagicMock, patch
import json

from super_brain.models import ThinkSlowResult, PersonalityDNA, SampleSummary


def test_think_slow_result_creation():
    """ThinkSlowResult should hold partial profile, confidence map, and focus list."""
    profile = PersonalityDNA(
        id="test",
        sample_summary=SampleSummary(
            total_tokens=0, conversation_count=0,
            date_range=["unknown", "unknown"],
            contexts=["test"], confidence_overall=0.5,
        ),
    )
    result = ThinkSlowResult(
        partial_profile=profile,
        confidence_map={"anxiety": 0.8, "trust": 0.3},
        low_confidence_traits=["trust"],
        observations=["Speaker avoids personal topics"],
    )
    assert result.low_confidence_traits == ["trust"]
    assert result.confidence_map["anxiety"] == 0.8
    assert len(result.observations) == 1


def test_think_slow_result_defaults():
    """ThinkSlowResult should have sensible defaults."""
    profile = PersonalityDNA(
        id="test",
        sample_summary=SampleSummary(
            total_tokens=0, conversation_count=0,
            date_range=["unknown", "unknown"],
            contexts=["test"], confidence_overall=0.5,
        ),
    )
    result = ThinkSlowResult(
        partial_profile=profile,
        confidence_map={},
        low_confidence_traits=[],
        observations=[],
    )
    assert result.low_confidence_traits == []
    assert result.confidence_map == {}


def test_think_slow_extract_returns_result():
    """ThinkSlow.extract() should return a ThinkSlowResult from conversation."""
    mock_response_data = {
        "observations": [
            "Speaker uses short, direct sentences — possible low gregariousness",
            "Avoids emotional topics — possible low feelings openness",
        ],
        "trait_estimates": [
            {"dimension": "EXT", "name": "gregariousness", "value": 0.30, "confidence": 0.6},
            {"dimension": "OPN", "name": "feelings", "value": 0.35, "confidence": 0.4},
            {"dimension": "NEU", "name": "anxiety", "value": 0.50, "confidence": 0.3},
        ],
    }

    with patch("super_brain.think_slow.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text=json.dumps(mock_response_data))]
        mock_client.messages.create.return_value = mock_resp

        from super_brain.think_slow import ThinkSlow
        ts = ThinkSlow(api_key="test-key")

        conversation = [
            {"role": "chatter", "text": "How's your day going?"},
            {"role": "speaker", "text": "Fine."},
            {"role": "chatter", "text": "Do anything fun?"},
            {"role": "speaker", "text": "Not really. Just work."},
        ]

        result = ts.extract(conversation, focus_traits=None, previous=None)

        assert result.partial_profile is not None
        assert len(result.partial_profile.traits) == 3
        assert "anxiety" in result.confidence_map
        # Low-confidence estimated traits are included
        assert "anxiety" in result.low_confidence_traits
        assert "feelings" in result.low_confidence_traits
        # High-confidence estimated trait is NOT low-confidence
        assert "gregariousness" not in result.low_confidence_traits
        # Unestimated traits are also low-confidence (they have no data at all)
        assert "narcissism" in result.low_confidence_traits  # not estimated → low conf


def test_think_slow_extract_with_focus_traits():
    """When focus_traits are provided, they should appear in the LLM prompt."""
    with patch("super_brain.think_slow.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text=json.dumps({
            "observations": [],
            "trait_estimates": [
                {"dimension": "SOC", "name": "social_dominance", "value": 0.50, "confidence": 0.5},
            ],
        }))]
        mock_client.messages.create.return_value = mock_resp

        from super_brain.think_slow import ThinkSlow
        ts = ThinkSlow(api_key="test-key")

        result = ts.extract(
            conversation=[{"role": "chatter", "text": "Hi"}, {"role": "speaker", "text": "Hello"}],
            focus_traits=["social_dominance", "humor_self_enhancing"],
            previous=None,
        )

        call_args = mock_client.messages.create.call_args
        user_msg = call_args[1]["messages"][0]["content"]
        assert "social_dominance" in user_msg
        assert "humor_self_enhancing" in user_msg


def test_simulate_conversation_with_think_slow():
    """simulate_conversation should accept a ThinkSlow and extract every 5 turns."""
    from unittest.mock import MagicMock, patch
    import json

    mock_ts_response = json.dumps({
        "observations": ["test observation"],
        "trait_estimates": [
            {"dimension": "EXT", "name": "warmth", "value": 0.50, "confidence": 0.5},
        ],
    })

    with patch("eval_conversation.anthropic.Anthropic") as mock_anthropic, \
         patch("super_brain.think_slow.anthropic.Anthropic") as mock_ts_anthropic:

        # Mock Chatter + Speaker
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="Test response")]
        mock_client.messages.create.return_value = mock_resp

        # Mock ThinkSlow
        mock_ts_client = MagicMock()
        mock_ts_anthropic.return_value = mock_ts_client
        mock_ts_resp = MagicMock()
        mock_ts_resp.content = [MagicMock(text=mock_ts_response)]
        mock_ts_client.messages.create.return_value = mock_ts_resp

        from eval_conversation import simulate_conversation, Chatter, PersonalitySpeaker
        from super_brain.think_slow import ThinkSlow
        from super_brain.profile_gen import generate_profile

        profile = generate_profile("test", seed=42)
        chatter = Chatter(api_key="test")
        speaker = PersonalitySpeaker(api_key="test")
        think_slow = ThinkSlow(api_key="test")

        conversation, ts_results = simulate_conversation(
            chatter, speaker, profile, n_turns=10, seed=0,
            think_slow=think_slow,
        )

        # Should have 2 ThinkSlow results (at turn 5 and turn 10)
        assert len(ts_results) == 2
        assert all(hasattr(r, "confidence_map") for r in ts_results)


def test_think_slow_generates_incisive_questions():
    """V2.3: ThinkSlow.extract() should generate incisive questions from trait gaps."""
    from unittest.mock import MagicMock, patch
    import json

    mock_response_data = {
        "observations": ["Speaker is brief and avoids personal topics"],
        "trait_estimates": [
            {"dimension": "EXT", "name": "warmth", "value": 0.40, "confidence": 0.6},
            {"dimension": "AGR", "name": "trust", "value": 0.50, "confidence": 0.3},
        ],
    }

    with patch("super_brain.think_slow.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text=json.dumps(mock_response_data))]
        mock_client.messages.create.return_value = mock_resp

        from super_brain.think_slow import ThinkSlow
        ts = ThinkSlow(api_key="test-key")

        conversation = [
            {"role": "chatter", "text": "How's your day?"},
            {"role": "speaker", "text": "Fine. Just work."},
        ]

        result = ts.extract(conversation, focus_traits=None, previous=None)

        # Should have incisive questions generated from low-confidence traits
        assert len(result.incisive_questions) > 0
        # Questions should target trait gaps
        targets = {q.target for q in result.incisive_questions}
        assert len(targets) > 0
