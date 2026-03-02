"""LLM Detector: Extract communication style features from conversation text."""

from __future__ import annotations

import json

import anthropic

from communication_dna.catalog import FEATURE_CATALOG, ALL_DIMENSIONS
from communication_dna.models import (
    CommunicationDNA,
    Feature,
    Evidence,
    SampleSummary,
)


_SYSTEM_PROMPT = """\
You are a communication style analyst. Given a conversation transcript and a target speaker, \
analyze that speaker's communication style across all provided feature dimensions.

For each feature, return:
- value: float [0.0, 1.0] based on the anchors provided
- intensity: float [0.0, 1.0] how prominent this feature is in their speech
- confidence: float [0.0, 1.0] your confidence in the assessment
- usage_probability: float [0.0, 1.0] how likely this feature appears in their speech
- stability: "stable" | "context_dependent" | "volatile"
- evidence: one short quote from the text supporting your assessment

Return ONLY valid JSON — an array of feature objects. No markdown, no explanation.
"""


def _build_feature_prompt(features: list[dict]) -> str:
    lines = ["Analyze these features:\n"]
    for f in features:
        lines.append(
            f"- dimension: {f['dimension']}, name: {f['name']}\n"
            f"  description: {f['description']}\n"
            f"  detection_hint: {f['detection_hint']}\n"
            f"  value 0.0 = {f['value_anchors']['0.0']}\n"
            f"  value 1.0 = {f['value_anchors']['1.0']}\n"
        )
    return "\n".join(lines)


class Detector:
    """Detect communication style features from conversation text using Claude."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        kwargs: dict = {"api_key": api_key}
        if api_key.startswith("sk-or-"):
            kwargs["base_url"] = "https://openrouter.ai/api"
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model

    def analyze(
        self,
        text: str,
        speaker_id: str,
        speaker_label: str,
        context: str = "general",
    ) -> CommunicationDNA:
        """Analyze a conversation and return a CommunicationDNA profile for the target speaker."""

        feature_prompt = _build_feature_prompt(FEATURE_CATALOG)
        user_message = (
            f"## Conversation Transcript\n\n{text}\n\n"
            f"## Target Speaker\n\nAnalyze speaker labeled '{speaker_label}'.\n\n"
            f"{feature_prompt}\n\n"
            f"Return a JSON array of objects, each with keys: "
            f"dimension, name, value, intensity, confidence, usage_probability, stability, evidence_quote"
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=16384,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text
        # Strip potential markdown fences
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = json.loads(raw)

        features: list[Feature] = []
        for item in parsed:
            features.append(
                Feature(
                    dimension=item["dimension"],
                    name=item["name"],
                    value=_clamp(item["value"]),
                    intensity=_clamp(item["intensity"]),
                    confidence=_clamp(item["confidence"]),
                    usage_probability=_clamp(item["usage_probability"]),
                    stability=item.get("stability", "stable"),
                    evidence=[Evidence(text=item.get("evidence_quote", ""), source="input_text")],
                )
            )

        token_count = len(text.split())
        return CommunicationDNA(
            id=speaker_id,
            sample_summary=SampleSummary(
                total_tokens=token_count,
                conversation_count=1,
                date_range=["unknown", "unknown"],
                contexts=[context],
                confidence_overall=sum(f.confidence for f in features) / max(len(features), 1),
            ),
            features=features,
        )


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))
