# tests/test_models.py
import json
from communication_dna.models import (
    Feature,
    ContextOverride,
    Evidence,
    SignaturePattern,
    FeatureRelation,
    DepthTrigger,
    DepthBarrier,
    DisclosureTrajectory,
    DepthProfile,
    SampleSummary,
    CommunicationDNA,
)


def test_feature_creation():
    f = Feature(
        dimension="LEX",
        name="formality",
        value=0.72,
        intensity=0.85,
        confidence=0.91,
        usage_probability=0.88,
        stability="stable",
    )
    assert f.dimension == "LEX"
    assert f.value == 0.72
    assert f.context_overrides == {}
    assert f.evidence == []


def test_feature_value_clamped():
    """Values must be in [0, 1]."""
    import pytest
    with pytest.raises(Exception):
        Feature(dimension="LEX", name="test", value=1.5, intensity=0.5, confidence=0.5, usage_probability=0.5)


def test_feature_with_context_overrides():
    f = Feature(
        dimension="LEX",
        name="formality",
        value=0.72,
        intensity=0.85,
        confidence=0.91,
        usage_probability=0.88,
        context_overrides={
            "work": ContextOverride(value=0.92, intensity=0.90),
            "casual": ContextOverride(value=0.35, intensity=0.70),
        },
        evidence=[
            Evidence(text="Indeed, I concur.", source="conv_001", timestamp="2026-03-01T14:30:00Z")
        ],
    )
    assert f.context_overrides["work"].value == 0.92
    assert len(f.evidence) == 1


def test_communication_dna_roundtrip():
    """Create a profile, serialize to JSON, deserialize back."""
    profile = CommunicationDNA(
        id="user_001",
        sample_summary=SampleSummary(
            total_tokens=5000,
            conversation_count=10,
            date_range=["2026-01-01", "2026-03-01"],
            contexts=["casual", "work"],
            confidence_overall=0.85,
        ),
        features=[
            Feature(
                dimension="LEX",
                name="formality",
                value=0.72,
                intensity=0.85,
                confidence=0.91,
                usage_probability=0.88,
            ),
        ],
        signature_patterns=[
            SignaturePattern(
                name="rhetorical-humor",
                features=["rhetorical_question", "irony", "short_sentence"],
                co_occurrence=0.82,
                frequency=0.15,
                context="casual",
            ),
        ],
        feature_relations=[
            FeatureRelation(
                source="formality",
                target="sentence_length",
                correlation=0.76,
                direction="positive",
            ),
        ],
        depth_profile=DepthProfile(
            baseline_depth=2.3,
            max_observed_depth=4,
            depth_triggers=[DepthTrigger(type="reciprocal_disclosure", effectiveness=0.8)],
            depth_barriers=[DepthBarrier(type="perceived_judgment", severity=0.9)],
            disclosure_trajectory=DisclosureTrajectory(warmup_turns=5, plateau_depth=3, deepening_rate=0.3),
        ),
    )

    json_str = profile.model_dump_json(indent=2)
    restored = CommunicationDNA.model_validate_json(json_str)
    assert restored.id == "user_001"
    assert len(restored.features) == 1
    assert restored.features[0].name == "formality"
    assert restored.depth_profile.baseline_depth == 2.3
