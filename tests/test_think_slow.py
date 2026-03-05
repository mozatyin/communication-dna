"""Tests for V2.1 Think Slow periodic extraction."""

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
