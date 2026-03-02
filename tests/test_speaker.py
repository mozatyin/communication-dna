# tests/test_speaker.py
import os

import pytest

from communication_dna.speaker import Speaker
from communication_dna.models import CommunicationDNA, Feature, SampleSummary


@pytest.fixture
def casual_profile() -> CommunicationDNA:
    """A profile representing a casual, colloquial, emoji-using speaker."""
    return CommunicationDNA(
        id="casual_speaker",
        sample_summary=SampleSummary(
            total_tokens=1000, conversation_count=5,
            date_range=["2026-01-01", "2026-03-01"],
            contexts=["casual"], confidence_overall=0.9,
        ),
        features=[
            Feature(dimension="LEX", name="formality", value=0.15, intensity=0.9, confidence=0.95, usage_probability=0.95),
            Feature(dimension="LEX", name="colloquialism", value=0.85, intensity=0.8, confidence=0.9, usage_probability=0.9),
            Feature(dimension="LEX", name="hedging_frequency", value=0.7, intensity=0.7, confidence=0.85, usage_probability=0.8),
            Feature(dimension="PRA", name="humor_frequency", value=0.75, intensity=0.8, confidence=0.9, usage_probability=0.7),
            Feature(dimension="PTX", name="emoji_usage", value=0.6, intensity=0.7, confidence=0.9, usage_probability=0.6),
            Feature(dimension="SYN", name="sentence_length", value=0.3, intensity=0.7, confidence=0.9, usage_probability=0.9),
        ],
    )


@pytest.fixture
def formal_profile() -> CommunicationDNA:
    """A profile representing a formal, precise speaker."""
    return CommunicationDNA(
        id="formal_speaker",
        sample_summary=SampleSummary(
            total_tokens=1000, conversation_count=5,
            date_range=["2026-01-01", "2026-03-01"],
            contexts=["work"], confidence_overall=0.9,
        ),
        features=[
            Feature(dimension="LEX", name="formality", value=0.92, intensity=0.9, confidence=0.95, usage_probability=0.95),
            Feature(dimension="LEX", name="colloquialism", value=0.05, intensity=0.1, confidence=0.9, usage_probability=0.1),
            Feature(dimension="SYN", name="sentence_complexity", value=0.8, intensity=0.85, confidence=0.9, usage_probability=0.9),
            Feature(dimension="PRA", name="directness", value=0.85, intensity=0.8, confidence=0.9, usage_probability=0.85),
        ],
    )


@pytest.fixture
def speaker() -> Speaker:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return Speaker(api_key=api_key)


def test_speaker_generates_text(speaker: Speaker, casual_profile: CommunicationDNA):
    result = speaker.generate(
        profile=casual_profile,
        content="Explain why testing is important in software development",
    )
    assert isinstance(result, str)
    assert len(result) > 20


def test_casual_vs_formal_style_differs(speaker: Speaker, casual_profile: CommunicationDNA, formal_profile: CommunicationDNA):
    content = "Explain why testing is important in software development"
    casual_output = speaker.generate(profile=casual_profile, content=content)
    formal_output = speaker.generate(profile=formal_profile, content=content)
    # Casual output should be less formal — simple heuristic check
    casual_lower = casual_output.lower()
    formal_lower = formal_output.lower()
    # At least one of these should differ meaningfully
    casual_signals = sum(1 for w in ["like", "kinda", "lol", "haha", "you know", "tbh", "gonna"] if w in casual_lower)
    formal_signals = sum(1 for w in ["furthermore", "therefore", "consequently", "essential", "critical", "imperative"] if w in formal_lower)
    assert casual_signals > 0 or formal_signals > 0, "Styles should produce detectably different outputs"
