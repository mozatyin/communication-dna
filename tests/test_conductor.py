"""Tests for V2.3 Conductor — dynamic probabilistic action selection."""

from super_brain.conductor import Conductor
from super_brain.models import (
    ThinkFastResult, ThinkSlowResult, ConductorAction, IncisiveQuestion,
    PersonalityDNA, SampleSummary,
)


def _make_think_slow(incisive_questions=None, info_staleness=0.5):
    """Helper to create a minimal ThinkSlowResult."""
    profile = PersonalityDNA(
        id="test",
        sample_summary=SampleSummary(
            total_tokens=0, conversation_count=0,
            date_range=["unknown", "unknown"],
            contexts=["test"], confidence_overall=0.5,
        ),
    )
    return ThinkSlowResult(
        partial_profile=profile,
        confidence_map={},
        low_confidence_traits=[],
        observations=[],
        incisive_questions=incisive_questions or [],
        info_staleness=info_staleness,
    )


def test_conductor_early_turns_listen():
    """Conductor should default to 'listen' in early turns."""
    conductor = Conductor()
    tf = ThinkFastResult(info_entropy=0.5)
    action = conductor.decide(think_fast=tf, think_slow=None, turn_number=2)
    assert action.mode == "listen"


def test_conductor_follows_opening():
    """When ThinkFast detects an opening, Conductor should follow it."""
    conductor = Conductor()
    tf = ThinkFastResult(opening="mentioned wanting to learn guitar", info_entropy=0.5)
    action = conductor.decide(think_fast=tf, think_slow=None, turn_number=6)
    assert action.mode == "follow_thread"
    assert "guitar" in action.context.lower()


def test_conductor_asks_when_stale():
    """When info is stale and questions exist, ask the top question."""
    conductor = Conductor()
    tf = ThinkFastResult(info_entropy=0.2)
    ts = _make_think_slow(
        incisive_questions=[
            IncisiveQuestion(
                question="When you're in a group, what role do you take?",
                target="social_dominance",
                priority=0.9,
                source="trait_gap",
            ),
        ],
        info_staleness=0.8,
    )
    action = conductor.decide(think_fast=tf, think_slow=ts, turn_number=8)
    assert action.mode == "ask_incisive"
    assert action.question is not None
    assert "group" in action.question.lower() or "role" in action.question.lower()


def test_conductor_keeps_listening_when_info_flowing():
    """When info_entropy is high, keep listening even if questions exist."""
    conductor = Conductor()
    tf = ThinkFastResult(info_entropy=0.8)
    ts = _make_think_slow(
        incisive_questions=[
            IncisiveQuestion(question="Some question", target="some_trait", priority=0.5),
        ],
        info_staleness=0.2,
    )
    action = conductor.decide(think_fast=tf, think_slow=ts, turn_number=10)
    assert action.mode == "listen"


def test_conductor_default_listen():
    """Without any signals, Conductor should default to listen."""
    conductor = Conductor()
    tf = ThinkFastResult()
    action = conductor.decide(think_fast=tf, think_slow=None, turn_number=5)
    assert action.mode == "listen"
