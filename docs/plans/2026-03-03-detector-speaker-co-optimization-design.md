# Communication DNA v1.1–v1.5: Speaker-Detector Co-Optimization Design

> **Date**: 2026-03-03
> **Baseline**: v1.0 (MAE 0.088, 70/72 ≤0.25)
> **Best historical**: v0.9 (MAE 0.072, 71/72 ≤0.25)

## 1. Problem Analysis

### 1.1 Per-Dimension MAE (v1.0)

| Dimension | MAE | Status |
|-----------|-----|--------|
| DSC (Disclosure) | 0.142 | Needs work |
| MET (Metalanguage) | 0.138 | Needs work |
| SYN (Syntax) | 0.115 | Improvable |
| PRA (Pragmatics) | 0.092 | Moderate |
| LEX (Lexical) | 0.086 | Moderate |
| AFF (Affect) | 0.078 | Acceptable |
| INT (Interaction) | 0.075 | Acceptable |
| DIS (Discourse) | 0.075 | Acceptable |
| PTX (Paralinguistic) | 0.042 | Good |
| ERR (Error) | 0.013 | Converged |

### 1.2 MISS Features (error > 0.25)

1. `casual_bro:hedging_frequency` — target 0.30, detected 0.65 (error 0.35)
   - Root cause: Speaker generates filler words ("like", "I guess") → Detector counts them as hedging
2. `anxious_hedger:ellipsis_frequency` — target 0.60, detected 0.275 (error 0.325)
   - Root cause: Detector under-counts ellipsis/trailing sentences

### 1.3 Systematic Bias Patterns

Detector consistently **over-estimates** abstract/subjective features:
- metacommentary: +0.15 to +0.175 across profiles
- vulnerability_willingness: +0.10 to +0.175
- disclosure_depth: +0.125 to +0.15
- emotion_word_density: +0.10 to +0.25 (anxious_hedger worst)
- colloquialism: +0.225 (anxious_hedger, hedging→casualness drift)

Detector consistently **under-estimates**:
- ellipsis_frequency: -0.30 to -0.325 (anxious_hedger)

### 1.4 EVALUATION.md Key Insights

- Self-preference bias: Same model (Claude Sonnet) for Speaker + Detector
- MET/DSC dimensions most susceptible to LLM subjective over-scoring
- n_samples=2 insufficient for stability (v0.9→v1.0 random variance ~0.016 MAE)
- hedging/filler confusion not addressed in calibration examples

## 2. Optimization Targets

| Metric | v1.0 | Target |
|--------|------|--------|
| Overall MAE | 0.088 | < 0.065 |
| ≤0.25 | 70/72 (97.2%) | 72/72 (100%) |
| MISS features | 2 | 0 |
| MET dimension MAE | 0.138 | < 0.08 |
| DSC dimension MAE | 0.142 | < 0.08 |
| SYN dimension MAE | 0.115 | < 0.07 |

## 3. Iteration Plan

### v1.1 — Detector: MET/DSC Few-Shot Calibration + Counting Instructions

**Files**: `communication_dna/detector.py`

**Changes**:

1. **MET/DSC few-shot calibration** — Add 2-3 examples per batch:
   - IDN,MET,TMP batch: Examples showing metacommentary at 0.25 vs 0.50 vs 0.75 levels. Key calibration: "a single 'I'm not explaining this well' is LOW (~0.25), not moderate"
   - AFF,INT,DSC batch: Examples showing vulnerability at moderate vs high. "Sharing a worry = 0.50-0.60, deep emotional exposure = 0.80+"

2. **Hedging vs filler distinction** — Add to LEX,SYN batch calibration:
   - "CRITICAL: Casual filler words ('like', 'I mean', 'you know', 'I guess') are NOT hedging markers. Hedging = epistemic uncertainty ('maybe', 'perhaps', 'probably', 'I think', 'it seems'). A casual text full of 'like' should score LOW hedging if statements are still confident."

3. **Ellipsis counting instruction** — Add to system prompt:
   - "For ellipsis_frequency: Count ALL instances of '...' and sentences that trail off or are syntactically incomplete. 0 instances = 0.0, 1-2 = 0.15-0.30, 3-5 = 0.40-0.60, 6-8 = 0.65-0.80, 9+ = 0.85+"

**Eval**: Run with baseline=v1.0, n_samples=2

### v1.2 — Speaker: Reduce Generation Ambiguity

**Files**: `communication_dna/speaker.py`

**Changes**:

1. **Hedging hard constraint refinement**:
   - For hedging < 0.40: "Use ONLY these hedge words: 'maybe', 'probably', 'I think'. Use exactly {N} hedge instances total. Do NOT use casual fillers ('like', 'I guess', 'kinda', 'I mean') as they will be misread as hedging."

2. **Ellipsis structural constraint strengthening**:
   - For ellipsis 0.55-0.75: "Include exactly 4-6 instances of '...' or trailing-off sentences. Make them visually obvious with the '...' character."

3. **New structural constraints for MET features**:
   - `self_correction_frequency`: Range-based instructions ("Correct yourself exactly {N} times with 'actually', 'wait no', 'let me rephrase'")
   - `metacommentary`: Range-based ("Include exactly {N} comments about how you're communicating: 'I'm rambling', 'not sure how to say this', 'does that make sense?'")

4. **emotion_word_density calibration offset**:
   - Add to CALIBRATION_OFFSETS. Speaker tends to over-generate emotion words. Points: (0.5, 0.30), (0.6, 0.40), (0.8, 0.65)

**Eval**: Run with baseline=v1.1

### v1.3 — Detector: Output Bias Correction

**Files**: `communication_dna/detector.py`

**Changes**:

1. **Post-detection calibration** — Apply correction to consistently biased features:
   ```
   DETECTOR_BIAS_CORRECTION = {
       "metacommentary": -0.10,      # consistently +0.15 across profiles
       "vulnerability_willingness": -0.08,  # consistently +0.10-0.175
       "disclosure_depth": -0.08,     # consistently +0.125-0.15
       "emotion_word_density": -0.05, # mild consistent over-estimation
   }
   ```
   Apply as: `corrected = max(0.0, min(1.0, raw_score + bias))`

2. **Conservative approach**: Only correct features with consistent direction across ALL profiles in v1.0 + v0.9 data. If a feature is over-estimated in some profiles but under-estimated in others, do NOT correct.

3. **Verify with data**: Cross-reference v0.9 and v1.0 error directions to confirm consistency before applying corrections.

**Eval**: Run with baseline=v1.2

### v1.4 — n_samples 2→3 + Variance Tracking

**Files**: `communication_dna/detector.py`, `eval_detector.py`

**Changes**:

1. **Increase n_samples to 3** in eval_detector.py default
2. **Track per-feature standard deviation** in `_detect_with_averaging`:
   - Return both mean and std for each feature
   - Flag features with std > 0.15 as "unstable"
3. **Confidence-weighted averaging**: If a sample's confidence is < 0.5, reduce its weight
4. **Add Spearman rank correlation** to eval output:
   - Per-profile: rank correlation between target values and detected values
   - Overall: aggregate Spearman ρ
5. **Add per-feature std to eval results JSON**

**Eval**: Run with baseline=v1.3, n_samples=3

### v1.5 — Final Tuning + Consistency Rules

**Files**: `communication_dna/detector.py`, `eval_detector.py`

**Changes**:

1. **Expand `_validate_consistency` rules**:
   - vulnerability_willingness + disclosure_depth correlation (should move together, gap ≤ 0.3)
   - metacommentary + self_correction positive correlation
   - emotion_word_density + empathy_expression should correlate for empathetic profiles
   - high hedging_frequency → low directness (strengthen existing rule)

2. **Parameter tuning** based on v1.1-v1.4 data:
   - Adjust bias corrections if over/under-corrected
   - Fine-tune few-shot examples based on which features improved vs regressed
   - Adjust structural constraints that didn't work as expected

3. **Stability test**: Run eval 3 times to measure run-to-run variance

**Eval**: Run with baseline=v1.4, n_samples=3

## 4. Iteration Protocol

Each version follows this process:

1. Make code changes (only ONE end: Speaker OR Detector per version)
2. Run eval: `ANTHROPIC_API_KEY=sk-or-... python eval_detector.py eval_results_v{prev}.json {n_samples}`
3. Save results as `eval_results_v{version}.json`
4. Compare against baseline:
   - Overall MAE: improved?
   - Per-dimension MAE: which improved, which regressed?
   - MISS count: reduced?
   - Any new MISS features? (regression check)
5. If regression > 0.01 MAE: investigate and potentially revert
6. Commit changes with eval results

## 5. Risk Mitigation

- **Over-optimization trap** (v0.5-v0.6 lesson): If fixing one profile breaks another, revert and try a more general approach
- **Random variance** (±0.016 MAE): Don't chase small improvements. Only count changes > 0.02 MAE as real signal
- **Speaker changes affect all profiles**: Test all 6 profiles, not just the targeted one
- **Bias correction overshoot**: Start conservative, increase gradually

## 6. Success Criteria

**Minimum success** (v1.5): MAE < 0.075, 71/72 ≤0.25
**Target**: MAE < 0.065, 72/72 ≤0.25
**Stretch**: MAE < 0.060
