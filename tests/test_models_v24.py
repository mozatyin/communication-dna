"""Tests for V2.4 data models: Fact, Reality, FactExtractionResult, Soul."""

from super_brain.models import (
    Fact, Reality, FactExtractionResult, Soul, PersonalityDNA, SampleSummary,
)


def test_fact_creation():
    f = Fact(category="career", content="software engineer at a startup", confidence=0.8, source_turn=3)
    assert f.category == "career"
    assert f.confidence == 0.8
    assert f.source_turn == 3


def test_fact_confidence_clamped():
    f = Fact(category="hobby", content="plays guitar", confidence=1.0, source_turn=1)
    assert f.confidence == 1.0


def test_reality_creation():
    r = Reality(
        summary="Currently a mid-career engineer exploring entrepreneurship",
        domains={"career": "software engineer", "relationships": "single"},
        constraints=["limited savings"],
        resources=["strong network"],
    )
    assert "engineer" in r.summary
    assert r.domains["career"] == "software engineer"
    assert len(r.constraints) == 1


def test_fact_extraction_result():
    result = FactExtractionResult(
        new_facts=[Fact(category="career", content="engineer", confidence=0.9, source_turn=5)],
        reality=Reality(
            summary="An engineer",
            domains={"career": "engineer"},
            constraints=[],
            resources=[],
        ),
        secrets=["avoids discussing family"],
        contradictions=["said values independence but hates decisions"],
    )
    assert len(result.new_facts) == 1
    assert result.reality is not None
    assert len(result.secrets) == 1
    assert len(result.contradictions) == 1


def test_fact_extraction_result_empty():
    result = FactExtractionResult(new_facts=[], reality=None, secrets=[], contradictions=[])
    assert len(result.new_facts) == 0
    assert result.reality is None


def test_soul_creation_minimal():
    profile = PersonalityDNA(
        id="test",
        sample_summary=SampleSummary(
            total_tokens=0, conversation_count=0,
            date_range=["unknown", "unknown"],
            contexts=["test"], confidence_overall=0.5,
        ),
    )
    soul = Soul(id="test_soul", character=profile)
    assert soul.id == "test_soul"
    assert soul.facts == []
    assert soul.reality is None
    assert soul.secrets == []
    assert soul.contradictions == []


def test_soul_with_facts():
    profile = PersonalityDNA(
        id="test",
        sample_summary=SampleSummary(
            total_tokens=0, conversation_count=0,
            date_range=["unknown", "unknown"],
            contexts=["test"], confidence_overall=0.5,
        ),
    )
    soul = Soul(
        id="test_soul",
        character=profile,
        facts=[
            Fact(category="career", content="engineer", confidence=0.9, source_turn=3),
            Fact(category="hobby", content="guitar", confidence=0.7, source_turn=5),
        ],
        reality=Reality(
            summary="An engineer who plays guitar",
            domains={"career": "engineer", "hobby": "guitar"},
            constraints=[],
            resources=["technical skills"],
        ),
        secrets=["enthusiasm spikes when discussing travel"],
    )
    assert len(soul.facts) == 2
    assert soul.reality is not None
    assert len(soul.secrets) == 1
