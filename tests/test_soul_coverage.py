"""Tests for V2.4 Soul Coverage scoring."""

from super_brain.models import (
    Soul, Fact, Reality, PersonalityDNA, SampleSummary,
)
from super_brain.soul_coverage import compute_soul_coverage


def _make_profile():
    return PersonalityDNA(
        id="test",
        sample_summary=SampleSummary(
            total_tokens=0, conversation_count=0,
            date_range=["u", "u"], contexts=["t"], confidence_overall=0.5,
        ),
    )


def test_empty_soul_coverage():
    soul = Soul(id="test", character=_make_profile())
    score = compute_soul_coverage(soul)
    assert score == 0.0


def test_full_soul_coverage():
    soul = Soul(
        id="test",
        character=_make_profile(),
        facts=[
            Fact(category="c", content=f"fact_{i}", confidence=0.9, source_turn=i)
            for i in range(10)
        ],
        reality=Reality(
            summary="Full reality",
            domains={"career": "engineer"},
            constraints=["time"],
            resources=["skills"],
        ),
        secrets=["s1", "s2", "s3"],
    )
    score = compute_soul_coverage(soul)
    assert score == 1.0


def test_partial_soul_coverage():
    soul = Soul(
        id="test",
        character=_make_profile(),
        facts=[
            Fact(category="c", content=f"fact_{i}", confidence=0.9, source_turn=i)
            for i in range(5)  # 5/10 = 0.5
        ],
        reality=Reality(
            summary="Partial",
            domains={},
            constraints=[],
            resources=[],
        ),
        # reality populated = 1.0
        secrets=["s1"],  # 1/3 = 0.333
    )
    score = compute_soul_coverage(soul)
    # (0.5 + 1.0 + 0.333) / 3 = 0.611
    assert abs(score - 0.611) < 0.01


def test_coverage_facts_cap():
    """More than 10 facts still gives 1.0 for facts component."""
    soul = Soul(
        id="test",
        character=_make_profile(),
        facts=[
            Fact(category="c", content=f"fact_{i}", confidence=0.9, source_turn=i)
            for i in range(20)
        ],
    )
    # 20 facts -> capped at 1.0 for facts, reality=0, secrets=0
    score = compute_soul_coverage(soul)
    assert abs(score - 1.0 / 3) < 0.01
