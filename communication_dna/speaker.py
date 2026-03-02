"""LLM Speaker: Generate text in a specific communication style."""

from __future__ import annotations

import anthropic

from communication_dna.models import CommunicationDNA, Feature
from communication_dna.catalog import ALL_DIMENSIONS


def _profile_to_style_instructions(profile: CommunicationDNA, intensity_scale: float = 1.0) -> str:
    """Convert a CommunicationDNA profile into natural-language style instructions."""
    lines = ["Adopt the following communication style:\n"]

    by_dim: dict[str, list[Feature]] = {}
    for f in profile.features:
        by_dim.setdefault(f.dimension, []).append(f)

    for dim_code, features in by_dim.items():
        dim_name = ALL_DIMENSIONS.get(dim_code, dim_code)
        lines.append(f"\n## {dim_name}")
        for f in features:
            scaled_value = min(1.0, f.value * intensity_scale)
            level = _value_to_level(scaled_value)
            lines.append(f"- {f.name}: {level} ({scaled_value:.2f}/1.0, prominence: {f.intensity:.2f})")

    return "\n".join(lines)


def _value_to_level(v: float) -> str:
    if v < 0.2:
        return "very low"
    if v < 0.4:
        return "low"
    if v < 0.6:
        return "moderate"
    if v < 0.8:
        return "high"
    return "very high"


class Speaker:
    """Generate text matching a CommunicationDNA profile."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def generate(
        self,
        profile: CommunicationDNA,
        content: str,
        intensity: float = 1.0,
        context: str | None = None,
    ) -> str:
        """Generate text expressing the given content in the profile's style.

        Args:
            profile: The CommunicationDNA profile to mimic.
            content: The semantic content to express.
            intensity: Style intensity multiplier (0.0 = neutral, 1.0 = full, >1.0 = exaggerated).
            context: Optional context label for context-dependent features.
        """
        style_instructions = _profile_to_style_instructions(profile, intensity_scale=intensity)

        system_prompt = (
            "You are a communication style actor. Your job is to express the user's content "
            "using EXACTLY the communication style described below. Do not add content beyond "
            "what is requested. Do not mention that you are acting or imitating. Just speak "
            "naturally in the described style.\n\n"
            f"{style_instructions}"
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Express this in the style described:\n\n{content}"}],
        )

        return response.content[0].text
