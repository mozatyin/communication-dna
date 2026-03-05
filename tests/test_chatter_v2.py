"""Tests for V2.0 Deep Listening Chatter."""

from eval_conversation import _build_chatter_system


def test_deep_listening_prompt_contains_10_components():
    """V2.0 chatter system prompt should reference Deep Listening principles."""
    prompt = _build_chatter_system(turn_number=1, total_turns=20)
    assert "attention" in prompt.lower() or "presence" in prompt.lower()
    assert "ease" in prompt.lower() or "no rush" in prompt.lower()
    assert "appreciation" in prompt.lower()


def test_deep_listening_phase_split():
    """Turns 1-14 = Deep Listening, Turns 15-20 = Incisive Questions."""
    early = _build_chatter_system(turn_number=3, total_turns=20)
    late = _build_chatter_system(turn_number=16, total_turns=20)
    assert "incisive" not in early.lower()
    assert "incisive" in late.lower() or "targeted" in late.lower()


def test_chatter_prompt_short_response_instruction():
    """Chatter should produce 1-2 sentence responses to maximize speaker output."""
    prompt = _build_chatter_system(turn_number=5, total_turns=20)
    assert "1-2 sentence" in prompt.lower() or "short" in prompt.lower()


def test_chatter_no_personality_probing():
    """Deep Listening should never directly probe personality."""
    for turn in [1, 5, 10, 15, 20]:
        prompt = _build_chatter_system(turn_number=turn, total_turns=20)
        assert "what kind of person" not in prompt.lower()
        assert "describe yourself" not in prompt.lower()


def test_chatter_max_tokens_reduced():
    """V2.0: Chatter should use max_tokens=150 (down from 256) for shorter responses."""
    from unittest.mock import MagicMock, patch

    with patch("eval_conversation.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="That's interesting, tell me more.")]
        mock_client.messages.create.return_value = mock_response

        from eval_conversation import Chatter
        chatter = Chatter(api_key="test-key")
        chatter.next_message(
            conversation=[{"role": "speaker", "text": "I had a great weekend."}],
            turn_number=3,
            total_turns=20,
        )

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] <= 150, (
            f"Chatter max_tokens should be ≤150, got {call_kwargs['max_tokens']}"
        )


def test_chatter_accepts_low_confidence_traits():
    """V2.2: _build_chatter_system should accept low_confidence_traits parameter."""
    from eval_conversation import _build_chatter_system

    prompt = _build_chatter_system(
        turn_number=16,
        total_turns=20,
        low_confidence_traits=["social_dominance", "humor_self_enhancing"],
    )

    # Late-phase prompt should include suggested topics for low-confidence traits
    lower_prompt = prompt.lower()
    assert "suggested" in lower_prompt or "exploration" in lower_prompt


def test_chatter_gap_aware_early_phase_ignores_traits():
    """Early phase should NOT inject gap-aware topics (not enough rapport)."""
    from eval_conversation import _build_chatter_system

    prompt = _build_chatter_system(
        turn_number=3,
        total_turns=20,
        low_confidence_traits=["social_dominance", "humor_self_enhancing"],
    )

    # Early turns should NOT have suggested exploration topics injected
    assert "suggested exploration" not in prompt.lower()
