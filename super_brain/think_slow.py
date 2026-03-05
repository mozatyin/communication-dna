"""Think Slow: Periodic personality extraction during conversation (V2.1).

Runs every 5 conversation turns to build an incremental confidence map
of detected traits. This enables gap-aware conversation steering in V2.2.
"""

from __future__ import annotations

import json
import re

import anthropic

from super_brain.catalog import TRAIT_CATALOG, ALL_DIMENSIONS
from super_brain.models import (
    PersonalityDNA, Trait, SampleSummary, ThinkSlowResult, Evidence,
    IncisiveQuestion,
)
from super_brain.trait_topic_map import get_topics_for_traits


_THINK_SLOW_SYSTEM = """\
You are analyzing a conversation to extract personality signals about the target speaker \
(labeled "Person B"). This is a PERIODIC check — you may have limited data. Be honest \
about uncertainty.

For each trait you can estimate:
1. Note specific observations from the text
2. Give a value (0.0-1.0) and confidence (0.0-1.0)
3. Confidence calibration (STRICT):
   - 0.1-0.2: vague impression, no direct evidence
   - 0.3-0.4: one indirect signal
   - 0.5-0.6: one clear signal or two indirect signals
   - 0.7-0.8: multiple clear, consistent signals
   - 0.9-1.0: overwhelming evidence (very rare in casual chat)

Return ONLY valid JSON:
{
  "observations": ["observation 1", "observation 2", ...],
  "trait_estimates": [
    {"dimension": "<DIM>", "name": "<trait_name>", "value": <float>, "confidence": <float>}
  ]
}

IMPORTANT:
- Only estimate traits you have SOME evidence for. Skip traits with zero signal.
- Default value for uncertain traits is 0.45-0.55 (population mean).
- This is casual conversation — apply LLM bias corrections (friendly tone ≠ high warmth, \
articulate text ≠ high cognition, etc.)
- Be CONSERVATIVE with confidence. In 5 turns of casual chat, most confidences should be \
0.2-0.5. Confidence > 0.7 requires MULTIPLE DISTINCT observations across different messages.
- Your confidence scores directly drive which traits get explored next. Over-confidence \
means we stop investigating traits that still need more evidence.
"""


def _format_conversation(conversation: list[dict]) -> str:
    """Format conversation for Think Slow input."""
    lines = []
    for msg in conversation:
        label = "Person A" if msg["role"] == "chatter" else "Person B"
        lines.append(f"{label}: {msg['text']}")
    return "\n\n".join(lines)


def _build_focus_section(focus_traits: list[str] | None) -> str:
    """Build a focus section for traits that need more attention."""
    if not focus_traits:
        return ""
    trait_info = []
    for t in TRAIT_CATALOG:
        if t["name"] in focus_traits:
            trait_info.append(
                f"- {t['name']} ({t['dimension']}): {t['description']}\n"
                f"  detection_hint: {t['detection_hint']}"
            )
    if not trait_info:
        return ""
    return (
        "\n\nFOCUS TRAITS — these were low-confidence in previous extraction. "
        "Pay special attention to any signal (even weak) for:\n"
        + "\n".join(trait_info)
    )


def _generate_incisive_questions(
    low_confidence_traits: list[str],
    confidence_map: dict[str, float],
    max_questions: int = 10,
) -> list[IncisiveQuestion]:
    """Generate incisive questions from trait gaps.

    Sorts traits by confidence (lowest first; unestimated traits get 0.0),
    maps them to natural conversation topics, and returns up to max_questions
    IncisiveQuestion objects.
    """
    # Sort by confidence ascending (unestimated traits get 0.0)
    sorted_traits = sorted(
        low_confidence_traits,
        key=lambda t: confidence_map.get(t, 0.0),
    )

    questions: list[IncisiveQuestion] = []
    for trait_name in sorted_traits:
        if len(questions) >= max_questions:
            break
        topics = get_topics_for_traits([trait_name], max_per_trait=1)
        conf = confidence_map.get(trait_name, 0.0)
        for topic in topics:
            if len(questions) >= max_questions:
                break
            questions.append(IncisiveQuestion(
                question=topic,
                target=trait_name,
                priority=1.0 - conf,
                source="trait_gap",
            ))

    return questions


class ThinkSlow:
    """Periodic personality extraction during conversation."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        kwargs: dict = {"api_key": api_key}
        if api_key.startswith("sk-or-"):
            kwargs["base_url"] = "https://openrouter.ai/api"
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model

    def extract(
        self,
        conversation: list[dict],
        focus_traits: list[str] | None = None,
        previous: ThinkSlowResult | None = None,
    ) -> ThinkSlowResult:
        """Extract personality signals from conversation so far."""
        conv_text = _format_conversation(conversation)
        focus_section = _build_focus_section(focus_traits)

        previous_section = ""
        if previous:
            prev_traits = {
                t.name: {"value": t.value, "confidence": previous.confidence_map.get(t.name, 0.5)}
                for t in previous.partial_profile.traits
            }
            previous_section = (
                f"\n\nPREVIOUS EXTRACTION (for anchoring — update, don't restart):\n"
                f"{json.dumps(prev_traits, indent=2)}"
            )

        user_message = (
            f"## Conversation\n\n{conv_text}\n\n"
            f"## Target Speaker\n\nAnalyze Person B's personality signals."
            f"{focus_section}{previous_section}\n\n"
            f"Return JSON with observations and trait_estimates."
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=_THINK_SLOW_SYSTEM,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text
        data = _parse_think_slow_response(raw)

        traits = []
        confidence_map: dict[str, float] = {}

        for est in data.get("trait_estimates", []):
            value = max(0.0, min(1.0, float(est["value"])))
            conf = max(0.0, min(1.0, float(est["confidence"])))
            traits.append(Trait(
                dimension=est["dimension"],
                name=est["name"],
                value=value,
                confidence=conf,
                evidence=[Evidence(text="think_slow", source="periodic_extraction")],
            ))
            confidence_map[est["name"]] = conf

        partial = PersonalityDNA(
            id="think_slow_partial",
            sample_summary=SampleSummary(
                total_tokens=len(conv_text.split()),
                conversation_count=1,
                date_range=["unknown", "unknown"],
                contexts=["think_slow"],
                confidence_overall=(
                    sum(confidence_map.values()) / max(len(confidence_map), 1)
                ),
            ),
            traits=traits,
        )

        # V2.2 fix: low_confidence includes BOTH low-confidence estimated traits
        # AND all catalog traits that weren't estimated at all (confidence = 0)
        all_trait_names = {t["name"] for t in TRAIT_CATALOG}
        estimated_names = set(confidence_map.keys())
        unestimated = all_trait_names - estimated_names

        low_conf = [name for name, conf in confidence_map.items() if conf < 0.5]
        # Unestimated traits are the MOST uncertain — add them all
        low_conf.extend(sorted(unestimated))

        incisive_qs = _generate_incisive_questions(
            low_confidence_traits=sorted(low_conf),
            confidence_map=confidence_map,
        )

        return ThinkSlowResult(
            partial_profile=partial,
            confidence_map=confidence_map,
            low_confidence_traits=sorted(low_conf),
            observations=data.get("observations", []),
            incisive_questions=incisive_qs,
        )


def _parse_think_slow_response(raw: str) -> dict:
    """Parse Think Slow JSON response."""
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass
    return {"observations": [], "trait_estimates": []}
