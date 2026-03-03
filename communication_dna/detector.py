"""LLM Detector: Extract communication style features from conversation text."""

from __future__ import annotations

import json
import re

import anthropic

from communication_dna.catalog import FEATURE_CATALOG, ALL_DIMENSIONS
from communication_dna.models import (
    CommunicationDNA,
    Feature,
    Evidence,
    SampleSummary,
)


# ── Batch definitions: group features by related dimensions ──────────────────

DIMENSION_BATCHES: list[list[str]] = [
    ["LEX", "SYN"],           # Batch 1: word choice + sentence structure (9 features)
    ["DIS", "PRA"],           # Batch 2: discourse + pragmatics (9 features)
    ["AFF", "INT", "DSC"],    # Batch 3: emotion + interaction + disclosure (11 features)
    ["IDN", "MET", "TMP"],    # Batch 4: identity + metalingual + temporal (9 features)
    ["ERR", "CSW", "PTX"],    # Batch 5: errors + code-switching + para-textual (9 features)
]


_SYSTEM_PROMPT = """\
You are a communication style analyst. Given a conversation transcript, a target speaker, \
and a set of feature dimensions to analyze, you must:

1. First, for EACH feature, list specific text observations (quotes, patterns, counts) \
that inform your assessment.
2. Then, provide a numeric score based on the anchor descriptions.

Return ONLY valid JSON with this structure:
{
  "reasoning": [
    {"feature": "<name>", "observations": ["observation 1", "observation 2", ...]}
  ],
  "scores": [
    {
      "dimension": "<DIM>",
      "name": "<feature_name>",
      "value": <float 0.0-1.0>,
      "intensity": <float 0.0-1.0>,
      "confidence": <float 0.0-1.0>,
      "usage_probability": <float 0.0-1.0>,
      "stability": "stable" | "context_dependent" | "volatile",
      "evidence_quote": "<short quote>"
    }
  ]
}

Guidelines:
- value: your assessment on the 0.0-1.0 scale, using the provided anchors as calibration points
- intensity: how prominent/noticeable this feature is in the speaker's text
- confidence: how certain you are (lower if insufficient evidence)
- usage_probability: how consistently this feature appears across the text
- stability: whether the feature is consistent or varies by context
- evidence_quote: a short direct quote from the text supporting your score

CALIBRATION GUIDELINES:
- Be precise. Use the anchor descriptions to calibrate your scores.
- A score of 0.25 should match the 0.25 anchor, 0.50 the 0.50 anchor, etc.
- COUNT BEFORE SCORING: For countable features, literally count instances before assigning a score.
- Common scoring errors to avoid:
  * Technical jargon alone does NOT mean high formality. Formality depends on sentence \
structure (contractions? passive voice?), register, and vocabulary formality. A text can be \
highly technical (jargon=0.9) but only moderately formal (formality=0.6) if it uses contractions \
and conversational structure.
  * HEDGING vs FILLERS: Hedging = epistemic uncertainty ('maybe', 'perhaps', 'probably', \
'I think', 'it seems', 'might be'). Casual fillers ('like', 'you know', 'I mean', 'I guess', \
'kinda') are NOT hedging — they are colloquialism markers. Count ONLY true hedge words. \
3-4 hedges across a long text is moderate (~0.30), not high. Reserve 0.70+ for texts where \
MOST statements are hedged with uncertainty markers.
  * Emotion words need literal counting. If a text mentions feelings/emotions in 2-3 sentences \
out of 10, that is moderate (~0.50), not high. Reserve 0.80+ for texts saturated with emotion words.
  * Sentence length should be estimated by counting actual words. 10-15 words average is low-moderate \
(~0.30), 15-20 is moderate (~0.50), 20-25 is moderately high (~0.65).
  * ELLIPSIS: Count all instances of '...' and syntactically incomplete/trailing sentences. \
0=0.00, 1-2=0.15-0.30, 3-5=0.40-0.60, 6-8=0.65-0.80, 9+=0.85+.
  * METACOMMENTARY: Count comments about HOW the speaker is communicating ('I\'m not explaining \
this well', 'does that make sense?', 'sorry I\'m rambling'). 0=0.00, 1=0.20-0.30, \
2=0.40-0.55, 3+=0.65+. Hedging ('I think') is NOT metacommentary.
  * VULNERABILITY: Sharing a worry/concern = moderate (0.40-0.60). Deep emotional exposure \
(fears, shame, trauma, crying) = high (0.75+). Do not inflate vulnerability just because \
the topic is personal.
  * Mid-range scores (0.35-0.65) are valid and often correct. Do not default to extremes.
"""


# ── Few-shot calibration examples per batch ─────────────────────────────────
# Short text snippets with known scores to ground the detector's scoring.

_BATCH_CALIBRATION_EXAMPLES: dict[str, str] = {
    "LEX,SYN": (
        "## Scoring Calibration Examples\n\n"
        "Example A — very casual, short sentences:\n"
        '"yo so like the thing is kinda messed up lol gonna try to fix it maybe"\n'
        "→ formality=0.05, colloquialism=0.95, sentence_length=0.15, sentence_complexity=0.10\n"
        "→ hedging_frequency=0.15 (only 'maybe' is a true hedge; 'like' and 'kinda' are casual fillers, NOT hedges)\n\n"
        "Example B — formal academic, long sentences:\n"
        '"The proposed methodology demonstrates significant advantages in computational efficiency, '
        'particularly when one considers the scalability constraints inherent in distributed systems."\n'
        "→ formality=0.95, vocabulary_richness=0.90, sentence_length=0.80, sentence_complexity=0.85\n\n"
        "Example C — technical but casual structure:\n"
        '"So basically you need to shard the database index — it\'s just a B-tree lookup, '
        'nothing fancy. The bottleneck is gonna be your I/O throughput."\n'
        "→ formality=0.35, jargon_density=0.80, colloquialism=0.65, sentence_length=0.40\n"
        "Note: high jargon does NOT automatically mean high formality.\n\n"
        "Example D — casual text with LOW hedging despite filler words:\n"
        '"Like, dude, I totally nailed that presentation, you know? I mean, it was honestly '
        'pretty awesome and everyone loved it. I guess that makes sense though."\n'
        "→ hedging_frequency=0.15, colloquialism=0.90\n"
        "CRITICAL: 'like', 'you know', 'I mean' are CASUAL FILLERS, not hedges. "
        "Only count epistemic uncertainty markers as hedging: 'maybe', 'perhaps', 'probably', "
        "'I think', 'it seems', 'might', 'could be'. A confident statement with filler words = LOW hedging.\n\n"
        "Example E — ellipsis counting:\n"
        '"So I was thinking... maybe we could try... I don\'t know... it\'s just that '
        'the whole thing feels... off somehow"\n'
        "→ ellipsis_frequency=0.75 (4 instances of '...')\n"
        "Count '...' and trailing-off sentences literally: "
        "0=0.0, 1-2=0.15-0.30, 3-5=0.40-0.60, 6-8=0.65-0.80, 9+=0.85+\n"
    ),
    "DIS,PRA": (
        "## Scoring Calibration Examples\n\n"
        "Example A — very direct, no humor:\n"
        '"The deadline is Friday. Send the report by 3pm. No exceptions."\n'
        "→ directness=0.95, humor_frequency=0.00, politeness_strategy=0.10\n\n"
        "Example B — indirect, polite, hedged:\n"
        '"I was wondering if maybe we could perhaps look into adjusting the timeline? '
        'No pressure at all, just a thought!"\n'
        "→ directness=0.10, politeness_strategy=0.90, humor_frequency=0.05\n\n"
        "Example C — moderate directness with light humor:\n"
        '"I think we should go with option B — it\'s simpler and honestly the other one '
        'gave me a headache just reading it. But hey, I\'m open to other ideas."\n'
        "→ directness=0.60, humor_frequency=0.40, politeness_strategy=0.50\n"
    ),
    "AFF,INT,DSC": (
        "## Scoring Calibration Examples\n\n"
        "Example A — emotionally saturated, high empathy:\n"
        '"Oh my heart just breaks for you, I\'m so sorry you\'re going through this. '
        'I totally understand that feeling of being completely overwhelmed and scared."\n'
        "→ emotion_word_density=0.90, empathy_expression=0.95, vulnerability_willingness=0.70\n\n"
        "Example B — factual with minimal emotion:\n"
        '"The results indicate a 15% decrease in throughput. We should investigate the cause."\n'
        "→ emotion_word_density=0.05, empathy_expression=0.05, question_frequency=0.10\n\n"
        "Example C — moderate emotion, some questions:\n"
        '"That\'s interesting, and I appreciate you sharing. How did that make you feel? '
        'I think there\'s something worth exploring there."\n'
        "→ emotion_word_density=0.45, empathy_expression=0.55, question_frequency=0.60\n\n"
        "Example D — high feedback signals (backchannels):\n"
        '"Right, I see what you mean. Yeah, that totally makes sense. Exactly — and I think '
        'the way you handled it was spot on. Mm-hmm, I get that."\n'
        "→ feedback_signal_frequency=0.80\n"
        "Note: feedback_signal_frequency measures backchannel markers (yeah, right, I see, mm-hmm, "
        "exactly, totally, got it, for sure). Count them literally across the text. "
        "3-4 across a long text is moderate (~0.40-0.50), 6-8 is high (~0.70).\n\n"
        "Example E — moderate vulnerability (sharing a concern, NOT deep exposure):\n"
        '"I\'ve been a bit stressed about the project deadline honestly. It\'s keeping me up some nights. '
        'But I think we\'ll figure it out."\n'
        "→ vulnerability_willingness=0.50, disclosure_depth=0.45\n"
        "IMPORTANT: Sharing a worry or concern = 0.40-0.60 vulnerability. "
        "Reserve 0.75+ for deep emotional exposure (fears, trauma, shame, crying). "
        "Simply mentioning stress or worry is MODERATE, not high.\n\n"
        "Example F — high vulnerability (deep emotional exposure):\n"
        '"I need to be honest... I\'ve been really struggling with depression lately. Some days I can\'t '
        'get out of bed. I feel like I\'m failing everyone around me and I don\'t know how to ask for help."\n'
        "→ vulnerability_willingness=0.85, disclosure_depth=0.80, emotion_word_density=0.75\n"
        "Note: disclosure_depth follows the same pattern — mentioning a topic = 0.40-0.55, "
        "sharing personal details/feelings about it = 0.60-0.75, deep intimate exposure = 0.80+.\n"
    ),
    "IDN,MET,TMP": (
        "## Scoring Calibration Examples\n\n"
        "Example A — high self-correction and metacommentary:\n"
        '"Well, actually no, let me rephrase that — I\'m not explaining this well. '
        'What I mean is... okay so basically I keep going back and forth on this. '
        'Sorry, I\'m rambling. Does that even make sense?"\n'
        "→ self_correction_frequency=0.85, metacommentary=0.80\n"
        "Note: This has 3+ meta-comments ('not explaining well', 'I\'m rambling', 'does that make sense') "
        "= HIGH metacommentary (0.75+).\n\n"
        "Example B — LOW metacommentary (~0.25):\n"
        '"I think the project is going well overall. The team has been productive and we\'re on track '
        'for the deadline. Not sure I\'m the best judge of the design choices though."\n'
        "→ metacommentary=0.25\n"
        "Note: ONE brief self-aware aside ('not sure I\'m the best judge') in an otherwise normal text "
        "= LOW (~0.20-0.30). This is NOT moderate.\n\n"
        "Example C — MODERATE metacommentary (~0.50):\n"
        '"I\'ve been thinking about this a lot. Honestly I\'m not sure I\'m explaining my reasoning well, '
        'but basically the architecture needs work. Let me try to put it differently — the coupling is too tight."\n'
        "→ metacommentary=0.50\n"
        "Note: TWO meta-comments ('not sure I\'m explaining well', 'let me try to put it differently') "
        "= MODERATE (~0.45-0.55). Count the instances.\n\n"
        "Example D — moderate definition tendency:\n"
        '"A load balancer — that\'s basically a traffic cop for your servers — distributes requests evenly."\n'
        "→ definition_tendency=0.60\n"
        "Note: providing ONE definition in a text is moderate (~0.50-0.65), not high. "
        "Reserve 0.80+ for texts that define MOST technical terms they use.\n"
    ),
    "ERR,CSW,PTX": (
        "## Scoring Calibration Examples\n\n"
        "Example A — heavy emoji and expressive punctuation:\n"
        '"OMG that is SO amazing!!! 🎉🎉🎉 I literally can\'t even!!! 😍"\n'
        "→ emoji_usage=0.95, expressive_punctuation=0.95, grammar_deviation=0.40\n\n"
        "Example B — no emoji, clean punctuation:\n"
        '"The analysis reveals three key findings, each of which merits further investigation."\n'
        "→ emoji_usage=0.00, expressive_punctuation=0.00, grammar_deviation=0.00\n\n"
        "Example C — moderate emoji (2-3 in a paragraph):\n"
        '"Had a great time at the meetup today 😊 Really enjoyed the talk on distributed systems. '
        'The food was decent too 👍"\n'
        "→ emoji_usage=0.40, expressive_punctuation=0.10\n"
    ),
}


def _get_calibration_examples(batch_dims: list[str]) -> str:
    """Get few-shot calibration examples for a batch."""
    key = ",".join(batch_dims)
    return _BATCH_CALIBRATION_EXAMPLES.get(key, "")


def _build_feature_prompt(features: list[dict]) -> str:
    """Build a prompt section describing features to analyze, with all anchor levels."""
    lines = ["Analyze these features:\n"]
    for f in features:
        anchors = f["value_anchors"]
        anchor_lines = []
        for key in ["0.0", "0.25", "0.50", "0.75", "1.0"]:
            if key in anchors:
                anchor_lines.append(f"    {key} = {anchors[key]}")

        lines.append(
            f"- dimension: {f['dimension']}, name: {f['name']}\n"
            f"  description: {f['description']}\n"
            f"  detection_hint: {f['detection_hint']}\n"
            f"  anchors:\n" + "\n".join(anchor_lines)
        )

        # Include correlation hints if available
        if "correlation_hints" in f:
            lines.append(f"  correlations: {f['correlation_hints']}")

        lines.append("")  # blank line between features

    return "\n".join(lines)


def _get_features_for_batch(batch_dims: list[str]) -> list[dict]:
    """Get catalog features for a batch of dimensions."""
    return [f for f in FEATURE_CATALOG if f["dimension"] in batch_dims]


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
        """Analyze a conversation and return a CommunicationDNA profile for the target speaker.

        Internally runs 5 batched LLM calls (one per dimension group) with chain-of-thought
        reasoning, then merges all features into a single profile.
        """

        all_features: list[Feature] = []

        for batch_dims in DIMENSION_BATCHES:
            batch_features = _get_features_for_batch(batch_dims)
            if not batch_features:
                continue

            dim_labels = ", ".join(
                f"{d} ({ALL_DIMENSIONS.get(d, d)})" for d in batch_dims
            )
            feature_prompt = _build_feature_prompt(batch_features)

            # Include few-shot calibration examples for this batch
            calibration = _get_calibration_examples(batch_dims)
            calibration_section = f"\n{calibration}\n" if calibration else ""

            user_message = (
                f"## Conversation Transcript\n\n{text}\n\n"
                f"## Target Speaker\n\nAnalyze speaker labeled '{speaker_label}'.\n\n"
                f"## Dimensions to Analyze: {dim_labels}\n\n"
                f"{feature_prompt}\n\n"
                f"{calibration_section}"
                f"Return JSON with 'reasoning' and 'scores' arrays as specified. "
                f"Analyze ONLY the {len(batch_features)} features listed above."
            )

            response = self._client.messages.create(
                model=self._model,
                max_tokens=8192,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )

            raw = response.content[0].text
            parsed = _parse_batch_response(raw)

            for item in parsed:
                all_features.append(
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

        # Post-process: validate consistency across batches
        all_features = _validate_consistency(all_features)

        token_count = len(text.split())
        return CommunicationDNA(
            id=speaker_id,
            sample_summary=SampleSummary(
                total_tokens=token_count,
                conversation_count=1,
                date_range=["unknown", "unknown"],
                contexts=[context],
                confidence_overall=sum(f.confidence for f in all_features) / max(len(all_features), 1),
            ),
            features=all_features,
        )


def _parse_batch_response(raw: str) -> list[dict]:
    """Parse a batch response that contains reasoning + scores."""
    # Strip markdown fences
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    # Try parsing as the expected {reasoning, scores} structure
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "scores" in data:
            return data["scores"]
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Try truncating to last complete object
    last_brace = raw.rfind("}")
    if last_brace != -1:
        # Find the outermost structure
        start = raw.find("{")
        if start != -1:
            try:
                data = json.loads(raw[start: last_brace + 1])
                if isinstance(data, dict) and "scores" in data:
                    return data["scores"]
            except json.JSONDecodeError:
                pass

        # Try as array
        start = raw.find("[")
        if start != -1:
            truncated = raw[start: last_brace + 1].rstrip().rstrip(",") + "\n]"
            try:
                return json.loads(truncated)
            except json.JSONDecodeError:
                pass

    # Last resort: extract individual objects with regex
    objects = []
    for m in re.finditer(r'\{[^{}]*\}', raw):
        try:
            obj = json.loads(m.group())
            # Only include objects that look like score entries
            if "dimension" in obj and "name" in obj and "value" in obj:
                objects.append(obj)
        except json.JSONDecodeError:
            continue
    if objects:
        return objects

    raise ValueError(f"Could not parse JSON from LLM response: {raw[:200]}...")


def _validate_consistency(features: list[Feature]) -> list[Feature]:
    """Check cross-feature correlations and resolve contradictions.

    Rules:
    - formality + colloquialism <= 1.3
    - directness + hedging_frequency <= 1.3
    - ellipsis_frequency > 0.7 => sentence_length < 0.5
    When violated, reduce the lower-confidence feature.
    """
    fmap: dict[str, Feature] = {f.name: f for f in features}

    # Rule 1: formality + colloquialism <= 1.3
    _apply_sum_constraint(fmap, "formality", "colloquialism", 1.3)

    # Rule 2: directness + hedging_frequency <= 1.3
    _apply_sum_constraint(fmap, "directness", "hedging_frequency", 1.3)

    # Rule 3: high ellipsis => short sentences
    if "ellipsis_frequency" in fmap and "sentence_length" in fmap:
        ell = fmap["ellipsis_frequency"]
        sl = fmap["sentence_length"]
        if ell.value > 0.7 and sl.value >= 0.5:
            # Reduce sentence_length if ellipsis confidence is higher
            if ell.confidence >= sl.confidence:
                new_val = min(sl.value, 0.45)
                fmap["sentence_length"] = Feature(
                    dimension=sl.dimension, name=sl.name, value=new_val,
                    intensity=sl.intensity, confidence=sl.confidence * 0.9,
                    usage_probability=sl.usage_probability, stability=sl.stability,
                    evidence=sl.evidence,
                )
            else:
                new_val = min(ell.value, 0.65)
                fmap["ellipsis_frequency"] = Feature(
                    dimension=ell.dimension, name=ell.name, value=new_val,
                    intensity=ell.intensity, confidence=ell.confidence * 0.9,
                    usage_probability=ell.usage_probability, stability=ell.stability,
                    evidence=ell.evidence,
                )

    return list(fmap.values())


def _apply_sum_constraint(
    fmap: dict[str, Feature], name_a: str, name_b: str, max_sum: float
) -> None:
    """If two features sum exceeds max_sum, reduce the lower-confidence one."""
    if name_a not in fmap or name_b not in fmap:
        return
    fa, fb = fmap[name_a], fmap[name_b]
    total = fa.value + fb.value
    if total <= max_sum:
        return
    excess = total - max_sum
    # Reduce the feature with lower confidence
    if fa.confidence < fb.confidence:
        new_val = max(0.0, fa.value - excess)
        fmap[name_a] = Feature(
            dimension=fa.dimension, name=fa.name, value=new_val,
            intensity=fa.intensity, confidence=fa.confidence * 0.9,
            usage_probability=fa.usage_probability, stability=fa.stability,
            evidence=fa.evidence,
        )
    else:
        new_val = max(0.0, fb.value - excess)
        fmap[name_b] = Feature(
            dimension=fb.dimension, name=fb.name, value=new_val,
            intensity=fb.intensity, confidence=fb.confidence * 0.9,
            usage_probability=fb.usage_probability, stability=fb.stability,
            evidence=fb.evidence,
        )


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))
