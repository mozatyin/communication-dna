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
    """When info_entropy is high (above threshold), keep listening even if questions exist."""
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


def test_conductor_force_probe_after_n_turns():
    """After max_turns_without_probe, force an incisive question even over openings."""
    conductor = Conductor(max_turns_without_probe=4)
    ts = _make_think_slow(
        incisive_questions=[
            IncisiveQuestion(question="Do you prefer routines?", target="order", priority=0.8),
        ],
    )
    # Simulate 4 turns of listening (turns 4-7, after 3 trust-building turns)
    for t in range(4, 8):
        tf = ThinkFastResult(info_entropy=0.6)  # above threshold
        conductor.decide(think_fast=tf, think_slow=ts, turn_number=t)

    # On turn 8, force-probe should fire even with an opening
    tf = ThinkFastResult(opening="travel plans", info_entropy=0.6)
    action = conductor.decide(think_fast=tf, think_slow=ts, turn_number=8)
    assert action.mode == "ask_incisive"
    assert "Force-probe" in action.context


def test_conductor_resets_counter_after_incisive():
    """After asking an incisive question, counter resets — next turn follows opening."""
    conductor = Conductor(max_turns_without_probe=4)
    ts = _make_think_slow(
        incisive_questions=[
            IncisiveQuestion(question="Q1", target="trust", priority=0.8),
        ],
    )
    # Force an ask via low entropy
    tf = ThinkFastResult(info_entropy=0.2)
    action = conductor.decide(think_fast=tf, think_slow=ts, turn_number=5)
    assert action.mode == "ask_incisive"

    # Next turn with opening should follow the opening (counter was reset)
    tf = ThinkFastResult(opening="dream job", info_entropy=0.5)
    action = conductor.decide(think_fast=tf, think_slow=ts, turn_number=6)
    assert action.mode == "follow_thread"


def test_conductor_prefers_unasked_targets():
    """Conductor should prefer traits that haven't been probed yet."""
    conductor = Conductor()
    ts = _make_think_slow(
        incisive_questions=[
            IncisiveQuestion(question="Q about trust", target="trust", priority=0.9),
            IncisiveQuestion(question="Q about order", target="order", priority=0.8),
        ],
    )
    # First ask picks highest priority (trust)
    tf = ThinkFastResult(info_entropy=0.2)
    action = conductor.decide(think_fast=tf, think_slow=ts, turn_number=5)
    assert action.question == "Q about trust"

    # Second ask should pick unasked target (order) even though trust has higher priority
    action = conductor.decide(think_fast=tf, think_slow=ts, turn_number=6)
    assert action.question == "Q about order"


def test_conductor_raised_entropy_threshold():
    """Entropy threshold is now 0.5 (was 0.3), so moderate responses trigger ask_incisive."""
    conductor = Conductor()
    ts = _make_think_slow(
        incisive_questions=[
            IncisiveQuestion(question="Q1", target="trust", priority=0.8),
        ],
    )
    # 0.4 entropy — was too high for old threshold (0.3), should work now
    tf = ThinkFastResult(info_entropy=0.4)
    action = conductor.decide(think_fast=tf, think_slow=ts, turn_number=5)
    assert action.mode == "ask_incisive"
