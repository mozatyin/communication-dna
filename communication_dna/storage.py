"""Save and load CommunicationDNA profiles to/from JSON files."""

from __future__ import annotations

from pathlib import Path

from communication_dna.models import CommunicationDNA


def save_profile(profile: CommunicationDNA, filepath: str | Path) -> None:
    """Save a CommunicationDNA profile to a JSON file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(profile.model_dump_json(indent=2))


def load_profile(filepath: str | Path) -> CommunicationDNA:
    """Load a CommunicationDNA profile from a JSON file."""
    path = Path(filepath)
    return CommunicationDNA.model_validate_json(path.read_text())
