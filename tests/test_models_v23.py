"""Tests for V2.3 models: ThinkFastResult, ConductorAction, IncisiveQuestion."""

from super_brain.models import ThinkFastResult, ConductorAction, IncisiveQuestion


def test_think_fast_result_creation():
    result = ThinkFastResult(
        new_facts=["works at a startup"],
        emotional_shift="became enthusiastic discussing travel",
        contradiction=None,
        opening="mentioned wanting to learn guitar",
        info_entropy=0.7,
    )
    assert result.new_facts == ["works at a startup"]
    assert result.emotional_shift == "became enthusiastic discussing travel"
    assert result.contradiction is None
    assert result.opening == "mentioned wanting to learn guitar"
    assert result.info_entropy == 0.7


def test_think_fast_result_defaults():
    result = ThinkFastResult()
    assert result.new_facts == []
    assert result.emotional_shift is None
    assert result.contradiction is None
    assert result.opening is None
    assert result.info_entropy == 0.5


def test_incisive_question_creation():
    q = IncisiveQuestion(
        question="What draws you to creative work?",
        target="aesthetics",
        priority=0.8,
        source="trait_gap",
    )
    assert q.question == "What draws you to creative work?"
    assert q.priority == 0.8
    assert q.source == "trait_gap"


def test_conductor_action_creation():
    action = ConductorAction(
        mode="ask_incisive",
        context="Low confidence on social_dominance",
        question="When you're in a group, what role do you naturally take?",
    )
    assert action.mode == "ask_incisive"
    assert action.question is not None


def test_conductor_action_listen_mode():
    action = ConductorAction(mode="listen", context="Building rapport")
    assert action.mode == "listen"
    assert action.question is None
