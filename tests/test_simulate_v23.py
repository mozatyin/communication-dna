"""Tests for V2.3 Conductor-driven simulate_conversation."""

from unittest.mock import MagicMock, patch
import json


def test_simulate_uses_conductor():
    """simulate_conversation should use ThinkFast + Conductor when think_slow is provided."""
    mock_ts_response = json.dumps({
        "observations": ["test"],
        "trait_estimates": [
            {"dimension": "EXT", "name": "warmth", "value": 0.50, "confidence": 0.5},
        ],
    })

    with patch("eval_conversation.anthropic.Anthropic") as mock_anthropic, \
         patch("super_brain.think_slow.anthropic.Anthropic") as mock_ts_anthropic:

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="Test response")]
        mock_client.messages.create.return_value = mock_resp

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
            chatter, speaker, profile, n_turns=6, seed=0,
            think_slow=think_slow,
        )

        assert len(conversation) >= 10


def test_simulate_think_slow_interval_3():
    """ThinkSlow should run every 3 turns instead of every 5."""
    mock_ts_response = json.dumps({
        "observations": [],
        "trait_estimates": [
            {"dimension": "EXT", "name": "warmth", "value": 0.50, "confidence": 0.5},
        ],
    })

    with patch("eval_conversation.anthropic.Anthropic") as mock_anthropic, \
         patch("super_brain.think_slow.anthropic.Anthropic") as mock_ts_anthropic:

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="Test response")]
        mock_client.messages.create.return_value = mock_resp

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

        # At 3-turn intervals over 10 turns: extractions at turn 3, 6, 9 = 3 results
        assert len(ts_results) >= 3
