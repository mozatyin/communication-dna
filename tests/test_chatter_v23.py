"""Tests for V2.3 Conductor-driven Chatter system prompt."""

from super_brain.models import ConductorAction


def test_build_chatter_from_action_listen():
    from eval_conversation import _build_chatter_from_action
    action = ConductorAction(mode="listen", context="Build rapport")
    prompt = _build_chatter_from_action(action)
    assert "deep listen" in prompt.lower() or "listen" in prompt.lower()
    assert "short" in prompt.lower() or "1-2 sentence" in prompt.lower()


def test_build_chatter_from_action_follow_thread():
    from eval_conversation import _build_chatter_from_action
    action = ConductorAction(
        mode="follow_thread",
        context="Follow up on: mentioned wanting to learn guitar",
    )
    prompt = _build_chatter_from_action(action)
    assert "guitar" in prompt.lower()
    assert "follow" in prompt.lower() or "explore" in prompt.lower()


def test_build_chatter_from_action_ask_incisive():
    from eval_conversation import _build_chatter_from_action
    action = ConductorAction(
        mode="ask_incisive",
        context="Target: social_dominance",
        question="When you're in a group, what role do you naturally take?",
    )
    prompt = _build_chatter_from_action(action)
    assert "role" in prompt.lower() or "group" in prompt.lower()
    assert "natural" in prompt.lower() or "weave" in prompt.lower()


def test_build_chatter_from_action_push():
    from eval_conversation import _build_chatter_from_action
    action = ConductorAction(
        mode="push",
        context="Explore contradiction: values independence but avoids decisions",
    )
    prompt = _build_chatter_from_action(action)
    assert "independence" in prompt.lower() or "contradiction" in prompt.lower()


def test_build_chatter_preserves_deep_listening_principles():
    from eval_conversation import _build_chatter_from_action
    for mode in ["listen", "follow_thread", "ask_incisive", "push"]:
        action = ConductorAction(mode=mode, context="test")
        prompt = _build_chatter_from_action(action)
        assert "attention" in prompt.lower() or "presence" in prompt.lower()
        assert "short" in prompt.lower() or "1-2 sentence" in prompt.lower()
