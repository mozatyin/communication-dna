# tests/test_matcher.py
import os

import pytest

from communication_dna.matcher import StyleMatcher, DepthLevel, MatcherResponse
from communication_dna.models import (
    CommunicationDNA, Feature, SampleSummary,
    DepthProfile, DepthTrigger, DepthBarrier, DisclosureTrajectory,
)


@pytest.fixture
def counterpart_profile() -> CommunicationDNA:
    return CommunicationDNA(
        id="counterpart",
        sample_summary=SampleSummary(
            total_tokens=2000, conversation_count=5,
            date_range=["2026-01-01", "2026-03-01"],
            contexts=["casual"], confidence_overall=0.85,
        ),
        features=[
            Feature(dimension="LEX", name="formality", value=0.3, intensity=0.8, confidence=0.9, usage_probability=0.9),
            Feature(dimension="PRA", name="directness", value=0.4, intensity=0.7, confidence=0.85, usage_probability=0.8),
            Feature(dimension="DSC", name="vulnerability_willingness", value=0.35, intensity=0.6, confidence=0.8, usage_probability=0.5),
        ],
        depth_profile=DepthProfile(
            baseline_depth=1.8,
            max_observed_depth=3,
            depth_triggers=[DepthTrigger(type="reciprocal_disclosure", effectiveness=0.8)],
            depth_barriers=[DepthBarrier(type="perceived_judgment", severity=0.7)],
            disclosure_trajectory=DisclosureTrajectory(warmup_turns=4, plateau_depth=2.5, deepening_rate=0.3),
        ),
    )


@pytest.fixture
def matcher() -> StyleMatcher:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return StyleMatcher(api_key=api_key)


def test_matcher_returns_response(matcher: StyleMatcher, counterpart_profile: CommunicationDNA):
    conversation_so_far = [
        {"role": "user", "text": "I've been thinking about switching careers lately."},
    ]
    result = matcher.respond(
        counterpart=counterpart_profile,
        conversation=conversation_so_far,
        goal="understand_deeper",
    )
    assert isinstance(result, MatcherResponse)
    assert isinstance(result.response_text, str)
    assert len(result.response_text) > 10
    assert isinstance(result.assessed_depth, DepthLevel)
    assert isinstance(result.target_depth, DepthLevel)


def test_matcher_assesses_depth_correctly(matcher: StyleMatcher, counterpart_profile: CommunicationDNA):
    # Level 1 statement (factual)
    conversation = [
        {"role": "user", "text": "I work in marketing at a tech company."},
    ]
    result = matcher.respond(counterpart=counterpart_profile, conversation=conversation, goal="understand_deeper")
    assert result.assessed_depth.value <= 2  # Should be L0-L1

    # Level 3 statement (emotional)
    conversation = [
        {"role": "user", "text": "Honestly, I'm terrified that I'm wasting my life in this job and I don't know how to change."},
    ]
    result = matcher.respond(counterpart=counterpart_profile, conversation=conversation, goal="understand_deeper")
    assert result.assessed_depth.value >= 2  # Should be L2-L3
