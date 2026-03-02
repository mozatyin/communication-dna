# tests/test_detector.py
import os
from pathlib import Path

import pytest

from communication_dna.detector import Detector
from communication_dna.models import CommunicationDNA


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_conversation() -> str:
    return (FIXTURES / "sample_conversation.txt").read_text()


@pytest.fixture
def detector() -> Detector:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return Detector(api_key=api_key)


def test_detector_returns_communication_dna(detector: Detector, sample_conversation: str):
    """Detector should return a valid CommunicationDNA profile."""
    profile = detector.analyze(
        text=sample_conversation,
        speaker_id="speaker_B",
        speaker_label="B",
    )
    assert isinstance(profile, CommunicationDNA)
    assert profile.id == "speaker_B"
    assert len(profile.features) > 0


def test_detector_detects_colloquial_style(detector: Detector, sample_conversation: str):
    """Speaker B uses colloquial language — detector should capture this."""
    profile = detector.analyze(
        text=sample_conversation,
        speaker_id="speaker_B",
        speaker_label="B",
    )
    colloquialism = next((f for f in profile.features if f.name == "colloquialism"), None)
    assert colloquialism is not None
    assert colloquialism.value > 0.5, "Speaker B is clearly colloquial"


def test_detector_detects_hedging(detector: Detector, sample_conversation: str):
    """Speaker B hedges frequently — detector should capture this."""
    profile = detector.analyze(
        text=sample_conversation,
        speaker_id="speaker_B",
        speaker_label="B",
    )
    hedging = next((f for f in profile.features if f.name == "hedging_frequency"), None)
    assert hedging is not None
    assert hedging.value > 0.4, "Speaker B hedges noticeably"


def test_detector_detects_emoji_usage(detector: Detector, sample_conversation: str):
    """Speaker B uses emoji — detector should capture this."""
    profile = detector.analyze(
        text=sample_conversation,
        speaker_id="speaker_B",
        speaker_label="B",
    )
    emoji = next((f for f in profile.features if f.name == "emoji_usage"), None)
    assert emoji is not None
    assert emoji.value > 0.2, "Speaker B uses some emoji"
