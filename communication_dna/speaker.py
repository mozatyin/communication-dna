"""LLM Speaker: Generate text in a specific communication style."""

from __future__ import annotations

import anthropic

from communication_dna.models import CommunicationDNA, Feature
from communication_dna.catalog import ALL_DIMENSIONS, FEATURE_CATALOG


# Pre-build a lookup from (dimension, name) -> catalog entry for anchor text
_CATALOG_MAP: dict[tuple[str, str], dict] = {
    (f["dimension"], f["name"]): f for f in FEATURE_CATALOG
}

# ── Calibration offsets v4 (exact v0.4 values) ──────────────────────────────
# v0.4 had the best eval: 97.2% ≤0.25, 100% ≤0.40.
# Reverted from v0.6 adjustments. Interaction warnings kept (trigger only for specific combos).

CALIBRATION_OFFSETS: dict[str, list[tuple[float, float]]] = {
    "formality": [
        (0.0, 0.0), (0.15, 0.05), (0.25, 0.10), (0.35, 0.20),
        (0.45, 0.30), (0.55, 0.35), (0.60, 0.38),
        (0.70, 0.45), (0.80, 0.60), (0.90, 0.80), (1.0, 1.0),
    ],
    "sentence_length": [
        (0.0, 0.0), (0.15, 0.0), (0.30, 0.05), (0.40, 0.10),
        (0.50, 0.20), (0.60, 0.35), (0.70, 0.45), (0.80, 0.60), (1.0, 1.0),
    ],
    "sentence_complexity": [
        (0.0, 0.0), (0.30, 0.10), (0.50, 0.25), (0.65, 0.45),
        (0.85, 0.70), (1.0, 1.0),
    ],
    "emoji_usage": [
        (0.0, 0.0), (0.20, 0.05), (0.40, 0.18), (0.50, 0.25),
        (0.60, 0.35), (0.70, 0.50), (0.80, 0.65), (1.0, 1.0),
    ],
    "colloquialism": [
        (0.0, 0.0), (0.25, 0.08), (0.40, 0.18), (0.50, 0.30),
        (0.65, 0.42), (0.80, 0.62), (0.90, 0.80), (1.0, 1.0),
    ],
    "vocabulary_richness": [
        (0.0, 0.0), (0.50, 0.25), (0.75, 0.55), (0.90, 0.80), (1.0, 1.0),
    ],
    "jargon_density": [
        (0.0, 0.0), (0.50, 0.30), (0.70, 0.50), (0.90, 0.75), (1.0, 1.0),
    ],
    "directness": [
        (0.0, 0.0), (0.25, 0.15), (0.40, 0.25), (0.50, 0.35),
        (0.60, 0.48), (0.80, 0.80), (0.90, 0.92), (0.95, 0.98), (1.0, 1.0),
    ],
    "hedging_frequency": [
        (0.0, 0.0), (0.15, 0.05), (0.30, 0.15), (0.50, 0.30),
        (0.70, 0.45), (0.85, 0.70), (0.95, 0.88), (1.0, 1.0),
    ],
    "emotion_word_density": [
        (0.0, 0.0), (0.25, 0.10), (0.40, 0.20), (0.50, 0.30),
        (0.60, 0.42), (0.70, 0.55), (0.80, 0.65), (0.90, 0.80), (1.0, 1.0),
    ],
    "humor_frequency": [
        (0.0, 0.0), (0.10, 0.0), (0.20, 0.10), (0.30, 0.20),
        (0.50, 0.42), (0.70, 0.62), (0.85, 0.80), (1.0, 1.0),
    ],
    "emotional_polarity_balance": [
        (0.0, 0.0), (0.25, 0.15), (0.50, 0.40), (0.65, 0.60),
        (0.75, 0.80), (0.85, 0.92), (1.0, 1.0),
    ],
    "empathy_expression": [
        (0.0, 0.0), (0.50, 0.40), (0.70, 0.65), (0.85, 0.88),
        (0.95, 1.00), (1.0, 1.0),
    ],
    "question_frequency": [
        (0.0, 0.0), (0.30, 0.15), (0.50, 0.35), (0.70, 0.55),
        (0.85, 0.75), (1.0, 1.0),
    ],
}


def _apply_calibration(feature_name: str, target_value: float, profile: CommunicationDNA | None = None) -> float:
    """Apply bias correction via linear interpolation on calibration points.

    For colloquialism, applies additional reduction when hedging is very high
    (since high hedging naturally inflates detected colloquialism).
    """
    if feature_name not in CALIBRATION_OFFSETS:
        return target_value
    points = CALIBRATION_OFFSETS[feature_name]
    if target_value <= points[0][0]:
        result = points[0][1]
    elif target_value >= points[-1][0]:
        result = points[-1][1]
    else:
        result = target_value
        for i in range(len(points) - 1):
            t_lo, p_lo = points[i]
            t_hi, p_hi = points[i + 1]
            if t_lo <= target_value <= t_hi:
                ratio = (target_value - t_lo) / (t_hi - t_lo) if t_hi != t_lo else 0
                result = p_lo + ratio * (p_hi - p_lo)
                break

    # Conditional: high hedging inflates colloquialism, so reduce further
    if feature_name == "colloquialism" and profile is not None:
        hedging = next((f.value for f in profile.features if f.name == "hedging_frequency"), 0)
        if hedging > 0.7 and 0.30 <= target_value <= 0.60:
            result = max(0.0, result - 0.10)

    return result


# ── Hard structural constraints ──────────────────────────────────────────────

_STRUCTURAL_CONSTRAINTS: dict[str, list[tuple[tuple[float, float], str]]] = {
    "ellipsis_frequency": [
        ((0.0, 0.15), "Never use ellipsis (...) or trailing-off sentences."),
        ((0.15, 0.35), "Use the '...' character at most once in the entire response. Write it as three dots explicitly."),
        ((0.35, 0.55), "Use the '...' character exactly 2-3 times. Leave 2-3 sentences trailing off or unfinished."),
        ((0.55, 0.75), "Use the '...' character exactly 3-4 times — NO MORE than 4. Write them explicitly as three dots. Count them carefully before finishing. Most sentences should be COMPLETE — only a few trail off with '...'."),
        ((0.75, 1.01), "Use '...' frequently throughout, at least 7 times. Many sentences trail off with '...' or remain unfinished."),
    ],
    "sentence_length": [
        ((0.0, 0.15), "Maximum 6 words per sentence. Use fragments and single-word responses freely. Ultra-terse."),
        ((0.15, 0.30), "Average 6-10 words per sentence. Maximum 14 words. Short and punchy."),
        ((0.30, 0.45), "Average 10-15 words per sentence. Maximum 20 words."),
        ((0.45, 0.60), "Average 15-20 words per sentence. Maximum 25 words."),
        ((0.60, 0.75), "Average 18-25 words per sentence."),
        ((0.75, 1.01), "Average 25+ words per sentence. Multi-clause constructions expected."),
    ],
    "emoji_usage": [
        ((0.0, 0.05), "Use exactly 0 emoji. None at all."),
        ((0.05, 0.25), "Use exactly 1 emoji in the entire response. Count: 1."),
        ((0.25, 0.45), "Use exactly 2 emoji total. Count them: 2."),
        ((0.45, 0.65), "Use exactly 3-4 emoji spread throughout the response. Count them."),
        ((0.65, 0.80), "Use 5-7 emoji spread throughout the response."),
        ((0.80, 1.01), "Use emoji liberally, at least one per sentence or two."),
    ],
    "formality": [
        ((0.0, 0.15), "Use slang freely. All contractions. Words like 'gonna', 'kinda', 'stuff', 'nah'. NO formal vocabulary."),
        ((0.15, 0.30), "Use contractions always. Casual vocabulary. Avoid any Latinate or academic words."),
        ((0.30, 0.50), "Use contractions often. Casual-to-standard vocabulary. No 'furthermore', 'consequently', 'moreover', 'henceforth'."),
        ((0.50, 0.70), "Use contractions sometimes. Mix casual and standard words. Avoid 'furthermore', 'consequently', 'nevertheless'. Keep vocabulary accessible."),
        ((0.70, 0.85), "Minimal contractions. Professional vocabulary. Avoid slang."),
        ((0.85, 1.01), "No contractions. Formal Latinate vocabulary. Academic register throughout."),
    ],
    "colloquialism": [
        ((0.0, 0.15), "Fully standard written English. No colloquial expressions at all."),
        ((0.15, 0.35), "Mostly standard with 1-2 casual expressions across the entire response."),
        ((0.35, 0.55), "Mix of standard and casual: use 3-5 colloquial expressions total. Contractions in roughly half of cases. NOT heavily slangy."),
        ((0.55, 0.75), "Predominantly casual. Frequent contractions, some slang, spoken-language patterns."),
        ((0.75, 1.01), "Heavily colloquial. Reads like transcribed speech. Frequent slang throughout."),
    ],
    "hedging_frequency": [
        ((0.0, 0.10), "No hedge words at all. Every statement definitive. Do NOT use 'like', 'I guess', 'kinda' either."),
        ((0.10, 0.25), "At most 1 hedge word (maybe/probably/I think) in the entire response. Casual fillers ('like', 'I mean', 'you know') are NOT hedges — avoid them unless colloquialism demands it."),
        ((0.25, 0.40), "Use exactly 2-3 hedge words total (maybe, I think, probably). Keep most statements definitive. IMPORTANT: 'like', 'I guess', 'I mean', 'kinda' are casual fillers, NOT hedges — do not count them as hedging."),
        ((0.40, 0.60), "Hedge about half of opinions. Mix definitive and tentative statements. Use: 'maybe', 'I think', 'probably', 'it seems'. Avoid casual fillers as hedge substitutes."),
        ((0.60, 0.80), "Hedge MOST but NOT ALL opinions. About 65-75% of statements should have a hedge word ('maybe', 'I think', 'probably', 'it seems'). Leave 25-35% of statements as clear, unhedged assertions. Do NOT hedge every single sentence."),
        ((0.80, 1.01), "Hedge nearly every statement. Rarely assert anything definitively."),
    ],
    "feedback_signal_frequency": [
        ((0.0, 0.20), "No backchannel responses (no 'yeah', 'right', 'I see', 'mm')."),
        ((0.20, 0.45), "Occasional backchannel (1-2 instances of 'yeah', 'right', 'I see')."),
        ((0.45, 0.65), "Regular backchannels. Start some sentences with 'Yeah', 'Right', 'I see', 'Mm'."),
        ((0.65, 0.85), "Frequent backchannels. Include at least 6-8 backchannel markers across the response: 'yeah', 'right', 'mm-hmm', 'I see', 'exactly', 'got it', 'absolutely', 'for sure'. Start several paragraphs with one."),
        ((0.85, 1.01), "Heavy backchanneling throughout. 'Yeah', 'totally', 'right', 'exactly' in almost every sentence."),
    ],
    "directness": [
        ((0.0, 0.15), "Always indirect. Never state opinions or requests explicitly. Use 'I wonder if...', 'Maybe we could...'."),
        ((0.15, 0.30), "Mostly indirect. Soften all statements. Use 'Perhaps', 'It might be worth considering'."),
        ((0.30, 0.50), "Balanced: sometimes direct ('I think X'), sometimes softened ('You might consider...'). Mix both approaches."),
        ((0.50, 0.70), "Lean direct. State views clearly but not bluntly."),
        ((0.70, 0.90), "Very direct. State opinions and requests plainly. 'I think X.' 'Do Y.'"),
        ((0.90, 1.01), "Extremely blunt. No softening at all. 'X is wrong.' 'Do Y now.'"),
    ],
}


def _get_structural_constraints(profile: CommunicationDNA) -> str:
    """Generate measurable structural constraints from feature values."""
    constraints: list[str] = []
    for f in profile.features:
        if f.name not in _STRUCTURAL_CONSTRAINTS:
            continue
        for (lo, hi), instruction in _STRUCTURAL_CONSTRAINTS[f.name]:
            if lo <= f.value < hi:
                constraints.append(f"- {f.name} ({f.value:.2f}): {instruction}")
                break
    return "\n".join(constraints)


# ── Spectrum anchoring ───────────────────────────────────────────────────────

def _generate_spectrum_constraints(profile: CommunicationDNA) -> str:
    """For mid-range features, show both extremes as boundaries to avoid."""
    constraints: list[str] = []

    for f in profile.features:
        # Skip features already covered by structural constraints
        if f.name in _STRUCTURAL_CONSTRAINTS:
            continue

        catalog_entry = _CATALOG_MAP.get((f.dimension, f.name))
        if not catalog_entry:
            continue
        anchors = catalog_entry.get("value_anchors", {})

        if 0.25 <= f.value <= 0.75:
            low_desc = anchors.get("0.0", "")
            high_desc = anchors.get("1.0", "")
            anchor_keys = sorted(float(k) for k in anchors)
            nearest = min(anchor_keys, key=lambda a: abs(a - f.value))
            nearest_key = f"{nearest:.2f}" if nearest not in (0.0, 1.0) else ("0.0" if nearest == 0.0 else "1.0")
            target_desc = anchors.get(nearest_key, "")

            direction = "slightly lower" if f.value < 0.50 else "slightly higher" if f.value > 0.50 else "dead center"
            constraints.append(
                f"- {f.name} ({f.value:.2f}): AIM FOR '{target_desc}'. "
                f"TOO LOW: '{low_desc}'. TOO HIGH: '{high_desc}'. "
                f"If unsure, err {direction}."
            )
        elif f.value < 0.25:
            high_desc = anchors.get("1.0", anchors.get("0.75", ""))
            if high_desc:
                constraints.append(
                    f"- {f.name} ({f.value:.2f}): Keep very low. "
                    f"NEVER drift toward '{high_desc}'."
                )
        else:  # > 0.75
            low_desc = anchors.get("0.0", anchors.get("0.25", ""))
            if low_desc:
                constraints.append(
                    f"- {f.name} ({f.value:.2f}): Keep very high. "
                    f"DO NOT fall to '{low_desc}'."
                )

    return "\n".join(constraints)


def _value_to_instruction(feature: Feature) -> str:
    """Convert a feature value to a 10-level description with nearest anchor text."""
    v = feature.value
    catalog_entry = _CATALOG_MAP.get((feature.dimension, feature.name))

    if v < 0.05:
        level = "negligible (essentially absent)"
    elif v < 0.15:
        level = "very low"
    elif v < 0.25:
        level = "low"
    elif v < 0.35:
        level = "low-moderate"
    elif v < 0.45:
        level = "moderate-low"
    elif v < 0.55:
        level = "moderate"
    elif v < 0.65:
        level = "moderate-high"
    elif v < 0.75:
        level = "high"
    elif v < 0.85:
        level = "high-very high"
    elif v < 0.95:
        level = "very high"
    else:
        level = "extreme (maximum)"

    anchor_text = ""
    if catalog_entry and "value_anchors" in catalog_entry:
        anchors = catalog_entry["value_anchors"]
        anchor_keys = sorted(float(k) for k in anchors)
        nearest = min(anchor_keys, key=lambda a: abs(a - v))
        anchor_text = anchors[f"{nearest:.2f}" if nearest not in (0.0, 1.0) else ("0.0" if nearest == 0.0 else "1.0")]

    desc = f"{level} ({v:.2f})"
    if anchor_text:
        desc += f" — {anchor_text}"
    return desc


def _profile_to_style_instructions(profile: CommunicationDNA, intensity_scale: float = 1.0) -> str:
    """Convert a CommunicationDNA profile into natural-language style instructions."""
    lines = ["<style_targets>"]

    by_dim: dict[str, list[Feature]] = {}
    for f in profile.features:
        by_dim.setdefault(f.dimension, []).append(f)

    for dim_code, features in by_dim.items():
        dim_name = ALL_DIMENSIONS.get(dim_code, dim_code)
        lines.append(f"\n## {dim_name}")
        for f in features:
            calibrated_value = _apply_calibration(f.name, f.value, profile)
            scaled_value = min(1.0, calibrated_value * intensity_scale)
            calibrated = Feature(
                dimension=f.dimension,
                name=f.name,
                value=scaled_value,
                intensity=f.intensity,
                confidence=f.confidence,
                usage_probability=f.usage_probability,
                stability=f.stability,
            )
            instruction = _value_to_instruction(calibrated)
            lines.append(f"- {f.name}: {instruction}")

    lines.append("</style_targets>")

    # Hard structural constraints
    structural = _get_structural_constraints(profile)
    if structural:
        lines.append("\n<hard_constraints>")
        lines.append("MEASURABLE RULES — verify these before outputting:")
        lines.append(structural)
        lines.append("</hard_constraints>")

    # Spectrum boundaries for features NOT covered by structural constraints
    spectrum = _generate_spectrum_constraints(profile)
    if spectrum:
        lines.append("\n<boundaries>")
        lines.append("BOUNDARY AWARENESS — stay between these extremes:")
        lines.append(spectrum)
        lines.append("</boundaries>")

    # Cross-feature interaction warnings
    interaction_warnings = _generate_interaction_warnings(profile)
    if interaction_warnings:
        lines.append("\n<interaction_warnings>")
        lines.append("IMPORTANT — feature interactions to watch for:")
        lines.append(interaction_warnings)
        lines.append("</interaction_warnings>")

    return "\n".join(lines)


def _generate_interaction_warnings(profile: CommunicationDNA) -> str:
    """Detect feature combinations that cause systematic drift and add warnings."""
    fmap = {f.name: f.value for f in profile.features}
    warnings: list[str] = []

    # High hedging/vulnerability/self-correction + mid formality → casual drift
    informal_drivers = sum([
        fmap.get("hedging_frequency", 0) > 0.6,
        fmap.get("vulnerability_willingness", 0) > 0.6,
        fmap.get("self_correction_frequency", 0) > 0.6,
        fmap.get("ellipsis_frequency", 0) > 0.5,
        fmap.get("expressive_punctuation", 0) > 0.5,
    ])
    if informal_drivers >= 2:
        if 0.30 <= fmap.get("formality", 0.5) <= 0.60:
            warnings.append(
                "- WARNING: This profile has high hedging/vulnerability/self-correction which "
                "naturally sounds casual. BUT formality must stay at MID-LEVEL. Do NOT let the "
                "hedging drag formality down. You can hedge while still using standard vocabulary. "
                "Example: 'I suppose one might argue that...' (hedged but not slangy)."
            )
        if 0.30 <= fmap.get("colloquialism", 0.5) <= 0.60:
            warnings.append(
                "- CRITICAL WARNING: Colloquialism MUST stay MODERATE (0.50 level) despite high hedging. "
                "Hedging naturally makes text sound casual — you MUST actively counteract this. "
                "Use STANDARD English hedge words: 'I think perhaps', 'it seems to me that', "
                "'one might consider'. NEVER use: 'like', 'I mean', 'kinda', 'idk', 'tbh', 'ngl'. "
                "Do NOT write as if transcribing speech. Write as if composing a thoughtful personal letter."
            )

    # Very high hedging + moderate colloquialism → colloquialism over-detection
    if fmap.get("hedging_frequency", 0) > 0.85 and 0.35 <= fmap.get("colloquialism", 0.5) <= 0.60:
        warnings.append(
            "- CRITICAL: With very high hedging, your text MUST NOT sound slangy or spoken-aloud. "
            "Use WRITTEN hedging: 'It seems', 'Perhaps', 'One might argue', 'I believe'. "
            "NEVER use spoken hedging: 'like maybe', 'idk', 'I guess kinda'. "
            "The colloquialism level is MODERATE — think 'thoughtful personal email', not 'text message'."
        )

    # High jargon + moderate formality → over-formalization
    if fmap.get("jargon_density", 0) > 0.7 and fmap.get("formality", 0.5) < 0.65:
        warnings.append(
            "- WARNING: High jargon with moderate formality. Technical vocabulary does NOT mean "
            "formal writing. Include some contractions ('it's', 'don't') and casual connectors "
            "('so', 'basically') to keep formality at the target level. Don't over-correct — "
            "aim for a mix of technical precision with accessible sentence structure."
        )

    # High formality + moderate directness → text often sounds too direct
    # The LLM tends to make formal academic text assertive, but we must not overcorrect.
    if fmap.get("formality", 0) > 0.80 and 0.25 <= fmap.get("directness", 0.5) <= 0.55:
        warnings.append(
            "- WARNING: Balance assertive and hedged claims. About 40% of statements should use "
            "hedging ('This suggests...', 'It appears that...', 'The evidence indicates...'). "
            "The remaining 60% can be moderately direct ('This finding is significant', "
            "'The analysis reveals X'). Do NOT make every sentence hedged — some clear assertions "
            "are expected in academic writing. Target a MODERATE directness level."
        )

    # High directness + low formality → text sounds less direct than intended
    if fmap.get("directness", 0) > 0.75 and fmap.get("formality", 0.5) < 0.20:
        warnings.append(
            "- WARNING: Very casual text can sound less direct because bro-speak uses hedging-like "
            "fillers. Make EVERY statement assertive. 'That's facts.' 'Nah.' 'Just do it.' 'Wrong.' "
            "Even amid casual language, be BLUNT. No 'kinda' or 'maybe' before opinions."
        )

    # High hedging + moderate-high ellipsis → ellipsis over-production
    if fmap.get("hedging_frequency", 0) > 0.80 and fmap.get("ellipsis_frequency", 0) >= 0.50:
        warnings.append(
            "- CRITICAL: High hedging MUST NOT create extra trailing patterns. Write hedged "
            "statements as COMPLETE sentences: 'I think perhaps we should consider that.' NOT "
            "'I think perhaps we should...' Count '...' strictly per the ellipsis constraint. "
            "Hedging uses WORDS (perhaps, maybe, might), not trailing punctuation."
        )

    # High hedging + moderate emotional_volatility → volatility under-expressed
    if fmap.get("hedging_frequency", 0) > 0.80 and fmap.get("emotional_volatility", 0) >= 0.50:
        warnings.append(
            "- IMPORTANT: Show EMOTIONAL SHIFTS within the text. Don't maintain one flat tone. "
            "Start uncertain, then become briefly more confident, then anxious again. "
            "Mix emotions: 'I think it could work — actually I'm really excited about this! "
            "But wait, what if it goes wrong...' The text must OSCILLATE between emotional states."
        )

    # High hedging + moderate vulnerability → vulnerability over-shoot
    if fmap.get("hedging_frequency", 0) > 0.80 and 0.55 <= fmap.get("vulnerability_willingness", 0.5) <= 0.75:
        warnings.append(
            "- WARNING: With high hedging, vulnerability easily over-shoots. Keep vulnerability "
            "at MODERATE-HIGH: share concerns but maintain composure. 'I'm a bit worried about...' "
            "YES. 'I'm genuinely terrified that...' NO. Stay in thoughtful-concern territory."
        )

    return "\n".join(warnings)


class Speaker:
    """Generate text matching a CommunicationDNA profile."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        kwargs: dict = {"api_key": api_key}
        if api_key.startswith("sk-or-"):
            kwargs["base_url"] = "https://openrouter.ai/api"
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model

    def generate(
        self,
        profile: CommunicationDNA,
        content: str,
        intensity: float = 1.0,
        context: str | None = None,
    ) -> str:
        """Generate text expressing the given content in the profile's style."""
        style_instructions = _profile_to_style_instructions(profile, intensity_scale=intensity)

        system_prompt = (
            "<role>\n"
            "You are a communication style actor. Express the user's content using EXACTLY "
            "the communication style described below. Do not add content beyond what is requested. "
            "Do not mention that you are acting or imitating. Just speak naturally in the described style.\n"
            "</role>\n\n"
            f"{style_instructions}"
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Express this in the style described:\n\n{content}"}],
        )

        return response.content[0].text
