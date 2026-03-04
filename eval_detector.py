"""Evaluate Detector accuracy by generating text from known profiles and re-detecting."""

import os
import json
import statistics
import sys
from pathlib import Path

from communication_dna.catalog import ALL_DIMENSIONS
from communication_dna.models import CommunicationDNA, Feature, SampleSummary
from communication_dna.speaker import Speaker
from communication_dna.detector import Detector


def make_profile(profile_id: str, features: list[dict]) -> CommunicationDNA:
    """Build a CommunicationDNA from a shorthand feature list."""
    return CommunicationDNA(
        id=profile_id,
        sample_summary=SampleSummary(
            total_tokens=0,
            conversation_count=0,
            date_range=["unknown", "unknown"],
            contexts=["evaluation"],
            confidence_overall=1.0,
        ),
        features=[
            Feature(
                dimension=f["dim"],
                name=f["name"],
                value=f["value"],
                intensity=f.get("intensity", 0.85),
                confidence=1.0,
                usage_probability=0.9,
                stability="stable",
            )
            for f in features
        ],
    )


# ── 6 distinct personas ──────────────────────────────────────────────────────

PROFILES = {
    "casual_bro": make_profile("casual_bro", [
        {"dim": "LEX", "name": "formality", "value": 0.05},
        {"dim": "LEX", "name": "colloquialism", "value": 0.95},
        {"dim": "LEX", "name": "hedging_frequency", "value": 0.3},
        {"dim": "SYN", "name": "sentence_length", "value": 0.15},
        {"dim": "SYN", "name": "sentence_complexity", "value": 0.1},
        {"dim": "SYN", "name": "ellipsis_frequency", "value": 0.8},
        {"dim": "PRA", "name": "directness", "value": 0.85},
        {"dim": "PRA", "name": "humor_frequency", "value": 0.8},
        {"dim": "AFF", "name": "emotion_word_density", "value": 0.6},
        {"dim": "PTX", "name": "emoji_usage", "value": 0.7},
        {"dim": "PTX", "name": "expressive_punctuation", "value": 0.8},
        {"dim": "ERR", "name": "grammar_deviation", "value": 0.7},
    ]),

    "formal_academic": make_profile("formal_academic", [
        {"dim": "LEX", "name": "formality", "value": 0.95},
        {"dim": "LEX", "name": "vocabulary_richness", "value": 0.9},
        {"dim": "LEX", "name": "jargon_density", "value": 0.7},
        {"dim": "LEX", "name": "colloquialism", "value": 0.05},
        {"dim": "SYN", "name": "sentence_length", "value": 0.8},
        {"dim": "SYN", "name": "sentence_complexity", "value": 0.85},
        {"dim": "SYN", "name": "passive_voice_preference", "value": 0.7},
        {"dim": "PRA", "name": "directness", "value": 0.4},
        {"dim": "PRA", "name": "humor_frequency", "value": 0.05},
        {"dim": "DIS", "name": "argumentation_style", "value": 0.85},
        {"dim": "PTX", "name": "emoji_usage", "value": 0.0},
        {"dim": "ERR", "name": "grammar_deviation", "value": 0.0},
    ]),

    "warm_empathetic": make_profile("warm_empathetic", [
        {"dim": "LEX", "name": "formality", "value": 0.35},
        {"dim": "LEX", "name": "hedging_frequency", "value": 0.7},
        {"dim": "PRA", "name": "politeness_strategy", "value": 0.9},
        {"dim": "PRA", "name": "directness", "value": 0.25},
        {"dim": "AFF", "name": "emotion_word_density", "value": 0.8},
        {"dim": "AFF", "name": "emotional_polarity_balance", "value": 0.75},
        {"dim": "AFF", "name": "empathy_expression", "value": 0.95},
        {"dim": "INT", "name": "question_frequency", "value": 0.7},
        {"dim": "INT", "name": "feedback_signal_frequency", "value": 0.7},
        {"dim": "DSC", "name": "vulnerability_willingness", "value": 0.8},
        {"dim": "DSC", "name": "disclosure_depth", "value": 0.7},
        {"dim": "PTX", "name": "emoji_usage", "value": 0.4},
    ]),

    "blunt_technical": make_profile("blunt_technical", [
        {"dim": "LEX", "name": "formality", "value": 0.6},
        {"dim": "LEX", "name": "jargon_density", "value": 0.9},
        {"dim": "LEX", "name": "vocabulary_richness", "value": 0.8},
        {"dim": "LEX", "name": "hedging_frequency", "value": 0.05},
        {"dim": "SYN", "name": "sentence_length", "value": 0.4},
        {"dim": "PRA", "name": "directness", "value": 0.95},
        {"dim": "PRA", "name": "humor_frequency", "value": 0.1},
        {"dim": "PRA", "name": "politeness_strategy", "value": 0.1},
        {"dim": "AFF", "name": "emotion_word_density", "value": 0.05},
        {"dim": "AFF", "name": "empathy_expression", "value": 0.05},
        {"dim": "PTX", "name": "emoji_usage", "value": 0.0},
        {"dim": "MET", "name": "definition_tendency", "value": 0.7},
    ]),

    "storyteller": make_profile("storyteller", [
        {"dim": "LEX", "name": "formality", "value": 0.4},
        {"dim": "LEX", "name": "vocabulary_richness", "value": 0.75},
        {"dim": "SYN", "name": "sentence_length", "value": 0.6},
        {"dim": "SYN", "name": "sentence_complexity", "value": 0.65},
        {"dim": "DIS", "name": "example_frequency", "value": 0.9},
        {"dim": "DIS", "name": "topic_transition_style", "value": 0.8},
        {"dim": "DIS", "name": "repetition_for_emphasis", "value": 0.7},
        {"dim": "PRA", "name": "humor_frequency", "value": 0.5},
        {"dim": "AFF", "name": "emotion_word_density", "value": 0.6},
        {"dim": "INT", "name": "turn_length", "value": 0.85},
        {"dim": "INT", "name": "response_elaboration", "value": 0.9},
        {"dim": "MET", "name": "metacommentary", "value": 0.5},
    ]),

    "anxious_hedger": make_profile("anxious_hedger", [
        {"dim": "LEX", "name": "formality", "value": 0.45},
        {"dim": "LEX", "name": "hedging_frequency", "value": 0.95},
        {"dim": "LEX", "name": "colloquialism", "value": 0.5},
        {"dim": "SYN", "name": "ellipsis_frequency", "value": 0.6},
        {"dim": "PRA", "name": "directness", "value": 0.1},
        {"dim": "PRA", "name": "politeness_strategy", "value": 0.8},
        {"dim": "AFF", "name": "emotion_word_density", "value": 0.5},
        {"dim": "AFF", "name": "emotional_volatility", "value": 0.6},
        {"dim": "MET", "name": "self_correction_frequency", "value": 0.8},
        {"dim": "MET", "name": "metacommentary", "value": 0.65},
        {"dim": "DSC", "name": "vulnerability_willingness", "value": 0.7},
        {"dim": "PTX", "name": "expressive_punctuation", "value": 0.65},
    ]),
}

# ── 10 prompts (expanded from 4) ────────────────────────────────────────────

PROMPTS = [
    # Original 4
    "Explain your thoughts on remote work vs. office work",
    "Describe how you handle disagreements with coworkers",
    "Talk about a mistake you made and what you learned",
    "Give your opinion on whether AI will replace most jobs",
    # New 6: targeted prompts
    "Tell a funny story about something that happened to you recently",         # humor_frequency
    "Walk me through how a database index works",                               # jargon_density, definition_tendency
    "React: your best friend just got their dream job after years of trying",   # empathy, emotion
    "Quick message to a friend about dinner plans tonight",                     # emoji, ellipsis, short sentences
    "Explain why you disagree with a popular opinion",                          # directness, argumentation
    "Describe something you're genuinely worried about right now",              # vulnerability, disclosure, hedging
]


def _detect_with_averaging(
    detector: Detector,
    conversation: str,
    profile_name: str,
    n_samples: int = 2,
) -> dict[str, float]:
    """Run detection n_samples times and average the results."""
    accumulated: dict[str, list[float]] = {}

    for i in range(n_samples):
        detected = detector.analyze(
            text=conversation,
            speaker_id=f"eval_{profile_name}_s{i}",
            speaker_label="Speaker",
        )
        for f in detected.features:
            key = f"{f.dimension}:{f.name}"
            accumulated.setdefault(key, []).append(f.value)

    return {key: statistics.mean(vals) for key, vals in accumulated.items()}


def run_eval(api_key: str, baseline_path: str | None = None, n_samples: int = 2):
    speaker = Speaker(api_key=api_key)
    detector = Detector(api_key=api_key)

    all_errors: list[float] = []
    dim_errors: dict[str, list[float]] = {}  # per-dimension error tracking
    results: dict[str, dict] = {}

    # Load baseline if provided
    baseline: dict | None = None
    if baseline_path and Path(baseline_path).exists():
        baseline = json.loads(Path(baseline_path).read_text())
        print(f"  Loaded baseline from {baseline_path}")

    for profile_name, profile in PROFILES.items():
        print(f"\n{'='*60}")
        print(f"  Profile: {profile_name}")
        print(f"{'='*60}")

        # Generate text
        print("  Generating text...", end=" ", flush=True)
        lines = []
        for prompt in PROMPTS:
            text = speaker.generate(profile=profile, content=prompt)
            lines.append(f"Speaker: {text}")
        conversation = "\n\n".join(lines)
        word_count = len(conversation.split())
        print(f"done ({word_count} words)")

        # Detect with multi-sample averaging
        print(f"  Detecting features ({n_samples} samples)...", end=" ", flush=True)
        detected_map = _detect_with_averaging(detector, conversation, profile_name, n_samples)
        print("done")

        # Compare
        profile_errors: list[float] = []
        feature_results: list[dict] = []

        original_map: dict[str, float] = {}
        for f in profile.features:
            original_map[f"{f.dimension}:{f.name}"] = f.value

        for key, original_val in original_map.items():
            detected_val = detected_map.get(key)
            if detected_val is None:
                print(f"    WARNING: {key} not found in detection output")
                continue
            error = abs(original_val - detected_val)
            profile_errors.append(error)
            all_errors.append(error)

            # Track per-dimension errors
            dim = key.split(":")[0]
            dim_errors.setdefault(dim, []).append(error)

            status = "OK" if error <= 0.25 else "MISS" if error <= 0.4 else "BAD"

            # Compute delta from baseline if available
            delta_str = ""
            if baseline and profile_name in baseline:
                bl_features = baseline[profile_name].get("features", [])
                bl_match = next((f for f in bl_features if f["feature"] == key), None)
                if bl_match:
                    delta = error - bl_match["error"]
                    delta_str = f"  Δ{delta:+.2f}"

            feature_results.append({
                "feature": key,
                "original": original_val,
                "detected": round(detected_val, 3),
                "error": round(error, 3),
                "status": status,
                "delta": delta_str,
            })

        # Sort by error descending
        feature_results.sort(key=lambda x: -x["error"])

        print(f"\n  {'Feature':<35} {'Orig':>6} {'Det':>6} {'Err':>6}  Status{' Δv0.1' if baseline else ''}")
        print(f"  {'-'*35} {'-'*6} {'-'*6} {'-'*6}  {'-'*6}{'------' if baseline else ''}")
        for r in feature_results:
            print(f"  {r['feature']:<35} {r['original']:>6.2f} {r['detected']:>6.2f} {r['error']:>6.3f}  {r['status']}{r['delta']}")

        mae = statistics.mean(profile_errors) if profile_errors else float("nan")
        within_025 = sum(1 for e in profile_errors if e <= 0.25)
        within_04 = sum(1 for e in profile_errors if e <= 0.4)
        total = len(profile_errors)

        print(f"\n  MAE: {mae:.3f} | Within 0.25: {within_025}/{total} | Within 0.40: {within_04}/{total}")

        results[profile_name] = {
            "mae": mae,
            "within_025": within_025,
            "within_04": within_04,
            "total": total,
            "features": feature_results,
        }

    # ── Per-dimension MAE report ───────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  PER-DIMENSION MAE")
    print(f"{'='*60}")
    print(f"\n  {'Dimension':<35} {'MAE':>6} {'Count':>6}")
    print(f"  {'-'*35} {'-'*6} {'-'*6}")
    for dim_code in sorted(dim_errors.keys()):
        errors = dim_errors[dim_code]
        dim_label = f"{dim_code} ({ALL_DIMENSIONS.get(dim_code, '?')})"
        print(f"  {dim_label:<35} {statistics.mean(errors):>6.3f} {len(errors):>6}")

    # ── Overall summary ───────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  OVERALL SUMMARY")
    print(f"{'='*60}")
    print(f"\n  {'Profile':<20} {'MAE':>6} {'<=0.25':>8} {'<=0.40':>8} {'Total':>6}")
    print(f"  {'-'*20} {'-'*6} {'-'*8} {'-'*8} {'-'*6}")
    for name, r in results.items():
        print(f"  {name:<20} {r['mae']:>6.3f} {r['within_025']:>8}/{r['total']:<4} {r['within_04']:>6}/{r['total']:<4}")

    overall_mae = statistics.mean(all_errors)
    overall_025 = sum(1 for e in all_errors if e <= 0.25)
    overall_04 = sum(1 for e in all_errors if e <= 0.4)
    total_features = len(all_errors)

    print(f"\n  Overall MAE: {overall_mae:.3f}")
    print(f"  Features within 0.25: {overall_025}/{total_features} ({100*overall_025/total_features:.1f}%)")
    print(f"  Features within 0.40: {overall_04}/{total_features} ({100*overall_04/total_features:.1f}%)")

    # ── Baseline comparison ───────────────────────────────────────────────
    if baseline:
        bl_mae = baseline.get("_overall", {}).get("mae")
        if bl_mae is not None:
            print(f"\n  v0.1 baseline MAE: {bl_mae:.3f} → v0.2 MAE: {overall_mae:.3f} (Δ{overall_mae - bl_mae:+.3f})")

    # ── Save results for future comparison ────────────────────────────────
    version_tag = "v1.2b"  # Update per release
    output_path = Path(f"eval_results_{version_tag}.json")
    save_data = dict(results)
    save_data["_overall"] = {
        "mae": overall_mae,
        "within_025": overall_025,
        "within_04": overall_04,
        "total": total_features,
    }
    save_data["_dim_mae"] = {
        dim: statistics.mean(errs) for dim, errs in dim_errors.items()
    }
    output_path.write_text(json.dumps(save_data, indent=2, default=str))
    print(f"\n  Results saved to {output_path}")

    return results


if __name__ == "__main__":
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Set ANTHROPIC_API_KEY env var to run evaluation.")
        sys.exit(1)

    baseline_path = sys.argv[1] if len(sys.argv) > 1 else None
    n_samples = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    run_eval(api_key, baseline_path=baseline_path, n_samples=n_samples)
