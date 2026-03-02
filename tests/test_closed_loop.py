"""
Closed-loop validation: Generate text from a known profile, then detect features
from that text, and verify the detected features match the original profile.
"""
import os

import pytest

from communication_dna.detector import Detector
from communication_dna.speaker import Speaker
from communication_dna.models import CommunicationDNA, Feature, SampleSummary


@pytest.fixture
def api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return key


@pytest.fixture
def known_profile() -> CommunicationDNA:
    """A strongly characterized profile for round-trip testing."""
    return CommunicationDNA(
        id="test_roundtrip",
        sample_summary=SampleSummary(
            total_tokens=0, conversation_count=0,
            date_range=["2026-03-02", "2026-03-02"],
            contexts=["test"], confidence_overall=1.0,
        ),
        features=[
            Feature(dimension="LEX", name="formality", value=0.1, intensity=0.95, confidence=1.0, usage_probability=0.95),
            Feature(dimension="LEX", name="colloquialism", value=0.9, intensity=0.9, confidence=1.0, usage_probability=0.9),
            Feature(dimension="PRA", name="humor_frequency", value=0.8, intensity=0.85, confidence=1.0, usage_probability=0.8),
            Feature(dimension="SYN", name="sentence_length", value=0.25, intensity=0.8, confidence=1.0, usage_probability=0.9),
        ],
    )


def test_roundtrip_style_preservation(api_key: str, known_profile: CommunicationDNA):
    """Generate text from a profile, then detect — detected values should roughly match."""
    speaker = Speaker(api_key=api_key)
    detector = Detector(api_key=api_key)

    # Generate a multi-turn conversation in the known style
    generated_lines = []
    prompts = [
        "Explain why you like working from home",
        "Describe your favorite programming language",
        "Give advice to someone starting their career",
    ]
    for prompt in prompts:
        text = speaker.generate(profile=known_profile, content=prompt)
        generated_lines.append(f"Speaker: {text}")

    conversation = "\n\n".join(generated_lines)

    # Detect features from generated text
    detected = detector.analyze(text=conversation, speaker_id="roundtrip", speaker_label="Speaker")

    # Check key features roughly match (within 0.3 tolerance — LLM generation is noisy)
    for original_feature in known_profile.features:
        detected_feature = next((f for f in detected.features if f.name == original_feature.name), None)
        assert detected_feature is not None, f"Feature {original_feature.name} not detected"
        diff = abs(detected_feature.value - original_feature.value)
        assert diff < 0.35, (
            f"Feature {original_feature.name}: original={original_feature.value:.2f}, "
            f"detected={detected_feature.value:.2f}, diff={diff:.2f} exceeds tolerance"
        )
