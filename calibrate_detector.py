"""Analyze eval results to compute optimal per-feature detector bias corrections.

Reads eval result JSON files and computes:
1. Per-feature signed errors across all profiles
2. Optimal flat offset corrections
3. Conditional corrections based on co-occurring features
"""

import json
import statistics
import sys
from pathlib import Path


def load_eval_results(paths: list[str]) -> list[dict]:
    """Load multiple eval result files."""
    results = []
    for p in paths:
        data = json.loads(Path(p).read_text())
        results.append(data)
    return results


def analyze_feature_errors(results: list[dict]) -> dict[str, list[dict]]:
    """Extract per-feature error data across all eval runs and profiles.

    Returns: {feature_name: [{profile, target, detected, signed_error}, ...]}
    """
    feature_data: dict[str, list[dict]] = {}

    for result in results:
        for profile_name, profile_data in result.items():
            if profile_name.startswith("_"):
                continue
            for f in profile_data.get("features", []):
                feature_key = f["feature"]  # e.g. "LEX:formality"
                name = feature_key.split(":")[1]
                signed_error = f["detected"] - f["original"]
                entry = {
                    "profile": profile_name,
                    "target": f["original"],
                    "detected": f["detected"],
                    "signed_error": signed_error,
                    "abs_error": f["error"],
                }
                feature_data.setdefault(name, []).append(entry)

    return feature_data


def compute_corrections(feature_data: dict[str, list[dict]]) -> list[dict]:
    """Compute optimal corrections for each feature."""
    corrections = []

    for name, entries in sorted(feature_data.items()):
        signed_errors = [e["signed_error"] for e in entries]
        abs_errors = [e["abs_error"] for e in entries]
        n = len(entries)

        # Average signed error = systematic bias
        mean_signed = statistics.mean(signed_errors)
        mean_abs = statistics.mean(abs_errors)

        # Check consistency: what fraction of errors are in the same direction?
        n_over = sum(1 for e in signed_errors if e > 0.02)
        n_under = sum(1 for e in signed_errors if e < -0.02)
        n_ok = n - n_over - n_under
        consistency = max(n_over, n_under) / n if n > 0 else 0

        # Simple linear calibration: find a, b minimizing sum of (a*detected + b - target)^2
        targets = [e["target"] for e in entries]
        detecteds = [e["detected"] for e in entries]

        # Grid search for optimal a, b
        best_mae = float("inf")
        best_a, best_b = 1.0, 0.0
        for a_int in range(50, 151, 5):  # a from 0.50 to 1.50
            a = a_int / 100
            for b_int in range(-20, 21, 1):  # b from -0.20 to 0.20
                b = b_int / 100
                calibrated = [max(0, min(1, a * d + b)) for d in detecteds]
                mae = statistics.mean(abs(c - t) for c, t in zip(calibrated, targets))
                if mae < best_mae:
                    best_mae = mae
                    best_a, best_b = a, b

        # Simple offset (a=1, just shift)
        best_offset = -mean_signed
        offset_mae = statistics.mean(
            abs(max(0, min(1, d + best_offset)) - t)
            for d, t in zip(detecteds, targets)
        )

        corrections.append({
            "name": name,
            "n_profiles": n,
            "mean_signed_error": round(mean_signed, 4),
            "mean_abs_error": round(mean_abs, 4),
            "consistency": round(consistency, 2),
            "direction": "over" if mean_signed > 0.02 else "under" if mean_signed < -0.02 else "mixed",
            "current_mae": round(mean_abs, 4),
            "offset_correction": round(best_offset, 3),
            "offset_mae": round(offset_mae, 4),
            "linear_a": round(best_a, 2),
            "linear_b": round(best_b, 2),
            "linear_mae": round(best_mae, 4),
        })

    return corrections


def print_report(corrections: list[dict]):
    """Print a formatted calibration report."""
    # Sort by current MAE descending
    corrections.sort(key=lambda c: -c["current_mae"])

    print(f"\n{'='*90}")
    print(f"  DETECTOR CALIBRATION ANALYSIS")
    print(f"{'='*90}")
    print(f"\n  {'Feature':<28} {'N':>3} {'SignedErr':>10} {'AbsErr':>8} {'Dir':>6} "
          f"{'Offset':>8} {'OffMAE':>8} {'LinA':>6} {'LinB':>6} {'LinMAE':>8}")
    print(f"  {'-'*28} {'-'*3} {'-'*10} {'-'*8} {'-'*6} {'-'*8} {'-'*8} {'-'*6} {'-'*6} {'-'*8}")

    for c in corrections:
        improved = ""
        if c["linear_mae"] < c["current_mae"] - 0.005:
            improved = " ★"
        print(f"  {c['name']:<28} {c['n_profiles']:>3} {c['mean_signed_error']:>+10.4f} "
              f"{c['mean_abs_error']:>8.4f} {c['direction']:>6} "
              f"{c['offset_correction']:>+8.3f} {c['offset_mae']:>8.4f} "
              f"{c['linear_a']:>6.2f} {c['linear_b']:>+6.2f} {c['linear_mae']:>8.4f}{improved}")

    # Summary
    print(f"\n  ★ = linear calibration improves MAE by >0.005")

    # Print recommended changes
    print(f"\n{'='*90}")
    print(f"  RECOMMENDED CORRECTIONS (features with consistent bias and improvement >0.005)")
    print(f"{'='*90}\n")

    for c in corrections:
        if c["linear_mae"] < c["current_mae"] - 0.005 and c["consistency"] > 0.5:
            improvement = c["current_mae"] - c["linear_mae"]
            print(f"  {c['name']}: a={c['linear_a']:.2f}, b={c['linear_b']:+.2f} "
                  f"(MAE {c['current_mae']:.3f} → {c['linear_mae']:.3f}, Δ-{improvement:.3f})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python calibrate_detector.py eval_results_v1.json [eval_results_v2.json ...]")
        sys.exit(1)

    results = load_eval_results(sys.argv[1:])
    feature_data = analyze_feature_errors(results)
    corrections = compute_corrections(feature_data)
    print_report(corrections)
