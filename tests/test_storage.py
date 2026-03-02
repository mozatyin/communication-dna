# tests/test_storage.py
import json
from pathlib import Path

import pytest

from communication_dna.storage import save_profile, load_profile
from communication_dna.models import CommunicationDNA, Feature, SampleSummary


@pytest.fixture
def sample_profile() -> CommunicationDNA:
    return CommunicationDNA(
        id="test_user",
        sample_summary=SampleSummary(
            total_tokens=1000, conversation_count=3,
            date_range=["2026-01-01", "2026-03-01"],
            contexts=["casual"], confidence_overall=0.85,
        ),
        features=[
            Feature(dimension="LEX", name="formality", value=0.5, intensity=0.7, confidence=0.9, usage_probability=0.8),
        ],
    )


def test_save_and_load_roundtrip(tmp_path: Path, sample_profile: CommunicationDNA):
    filepath = tmp_path / "profiles" / "test_user.json"
    save_profile(sample_profile, filepath)
    assert filepath.exists()

    loaded = load_profile(filepath)
    assert loaded.id == sample_profile.id
    assert len(loaded.features) == 1
    assert loaded.features[0].name == "formality"


def test_save_creates_directories(tmp_path: Path, sample_profile: CommunicationDNA):
    filepath = tmp_path / "deep" / "nested" / "profile.json"
    save_profile(sample_profile, filepath)
    assert filepath.exists()
