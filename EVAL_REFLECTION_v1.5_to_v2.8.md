# Communication DNA Eval Reflection: v1.5 through v2.8

**Analysis Date:** 2026-03-08
**Versions Analyzed:** v1.5, v1.6, v1.7, v1.8, v1.9, v2.0, v2.1, v2.2, v2.3, v2.4, v2.5, v2.6, v2.7, v2.8
**Stability Runs:** v2.5 (original), v2.5_run1, v2.5_run2, v2.5_run3
**Features Tracked:** 72 (6 profiles x 12 features)
**Profiles:** casual_bro, formal_academic, warm_empathetic, blunt_technical, storyteller, anxious_hedger

---

## Executive Summary

Overall system MAE improved from **0.0682** (v1.5) to a best of **0.0466** (v2.7), a **31.7% reduction**. However, v2.8 regressed to 0.0503, indicating that recent changes traded improvements in some features for regressions in others. The system has reached a point where most remaining error falls into four distinct categories, each requiring fundamentally different intervention strategies.

### Overall MAE Trajectory

| Version | MAE    | Delta from v1.5 |
|---------|--------|------------------|
| v1.5    | 0.0682 | --               |
| v1.6    | 0.0545 | -0.0137          |
| v1.7    | 0.0519 | -0.0163          |
| v1.8    | 0.0574 | -0.0108          |
| v1.9    | 0.0597 | -0.0085          |
| v2.0    | 0.0610 | -0.0072          |
| v2.1    | 0.0592 | -0.0090          |
| v2.2    | 0.0536 | -0.0146          |
| v2.3    | 0.0518 | -0.0164          |
| v2.4    | 0.0538 | -0.0144          |
| v2.5    | 0.0533 | -0.0149          |
| v2.6    | 0.0476 | -0.0206          |
| v2.7    | **0.0466** | **-0.0216**  |
| v2.8    | 0.0503 | -0.0179          |

### Profile MAE at v2.7 (Best Overall)

| Profile           | v1.5 MAE | v2.7 MAE | Improvement |
|-------------------|----------|----------|-------------|
| formal_academic   | 0.042    | 0.027    | 35.7%       |
| warm_empathetic   | 0.073    | 0.036    | 50.7%       |
| storyteller       | 0.061    | 0.039    | 36.1%       |
| blunt_technical   | 0.065    | 0.048    | 26.2%       |
| casual_bro        | 0.080    | 0.053    | 33.8%       |
| anxious_hedger    | 0.088    | 0.076    | 13.6%       |

**Key observation:** anxious_hedger has seen the least improvement (13.6%) and remains the worst-performing profile by a wide margin. It has never achieved MAE below 0.049 (v2.0).

---

## Category 1: Irreducible Noise Features

**Definition:** Error fluctuates randomly (+/-0.05-0.10) across versions with no consistent direction. These features flip between OVER and UNDER detection across versions and show high between-run stability variance, meaning the error is substantially driven by LLM generation stochasticity rather than systematic prompt or detection issues.

**Identifying criteria:**
- Direction flips between OVER and UNDER (neither exceeds 70% of versions)
- Mean error 0.02-0.10
- Stability std >= 0.01 across v2.5 repeated runs

### Features (16 total)

| Feature | Mean Error | Stab Std | Error Range | Over/Under |
|---------|-----------|----------|-------------|------------|
| storyteller:PRA:humor_frequency | 0.093 | 0.058 | 0.217 | 5/9 |
| storyteller:MET:metacommentary | 0.074 | 0.039 | 0.183 | 7/7 |
| anxious_hedger:AFF:emotional_volatility | 0.075 | 0.037 | 0.200 | 8/5 |
| blunt_technical:AFF:empathy_expression | 0.021 | 0.033 | 0.050 | 2/7 |
| formal_academic:DIS:argumentation_style | 0.035 | 0.029 | 0.100 | 9/0 |
| blunt_technical:SYN:sentence_length | 0.054 | 0.029 | 0.150 | 6/5 |
| anxious_hedger:PRA:directness | 0.031 | 0.029 | 0.050 | 8/3 |
| casual_bro:PTX:expressive_punctuation | 0.041 | 0.026 | 0.094 | 9/5 |
| casual_bro:AFF:emotion_word_density | 0.046 | 0.025 | 0.150 | 8/2 |
| casual_bro:ERR:grammar_deviation | 0.031 | 0.025 | 0.067 | 4/6 |
| warm_empathetic:AFF:emotion_word_density | 0.026 | 0.025 | 0.050 | 6/4 |
| blunt_technical:LEX:vocabulary_richness | 0.032 | 0.025 | 0.100 | 9/0 |
| blunt_technical:LEX:jargon_density | 0.022 | 0.025 | 0.050 | 7/2 |
| storyteller:LEX:vocabulary_richness | 0.033 | 0.025 | 0.050 | 4/8 |
| anxious_hedger:MET:self_correction_frequency | 0.030 | 0.025 | 0.067 | 7/3 |
| formal_academic:SYN:passive_voice_preference | 0.041 | 0.014 | 0.100 | 5/8 |

### Interpretation

These 16 features represent the noise floor of the system. Their error is fundamentally driven by run-to-run variability in the LLM speaker's text generation. Key patterns:

1. **Humor frequency** (storyteller) has the highest noise: stability std = 0.058, meaning a single re-run shifts error by +/-6 points on average. This makes sense -- humor is the most stochastic aspect of natural language generation.

2. **Emotional volatility** (anxious_hedger) at stability std = 0.037 reflects the inherent difficulty of generating text with precisely controlled emotional variation. Each generation produces different emotional arcs.

3. **Sentence length** (blunt_technical) flips direction because the blunt_technical target (0.35) sits near the natural center of LLM output, so small generation shifts push it either way.

4. Most of these features have mean errors under 0.05, meaning they contribute relatively little to overall MAE. The noise is real but small.

**Recommendation:** Accept these as the noise floor. Do not attempt to optimize them further -- doing so will overfit to specific generation runs and cause regressions elsewhere. The appropriate mitigation is **multi-run averaging** at eval time (which the stability runs already support).

---

## Category 2: Systematic Bias Features

**Definition:** Error consistently points in one direction (OVER or UNDER) across 5+ versions, indicating a structural mismatch between what the speaker produces and what the detector expects (or what the prompt instructs vs. what the LLM can deliver).

**Identifying criteria:**
- Direction consistency >= 70% in one direction
- Mean error >= 0.03

### Features (39 total -- showing top 20 by mean error)

| # | Feature | Dir | Mean Err | v2.7 Err | Consistency | Stab Std |
|---|---------|-----|----------|----------|-------------|----------|
| 1 | formal_academic:PRA:directness | OVER | 0.156 | 0.050 | 11/14 over | 0.025 |
| 2 | anxious_hedger:SYN:ellipsis_frequency | OVER | 0.145 | 0.200 | 14/14 over | 0.029 |
| 3 | casual_bro:SYN:sentence_length | OVER | 0.131 | 0.100 | 14/14 over | 0.048 |
| 4 | blunt_technical:LEX:formality | OVER | 0.113 | 0.030 | 10/14 over | 0.098 |
| 5 | warm_empathetic:LEX:hedging_frequency | OVER | 0.112 | 0.050 | 14/14 over | 0.025 |
| 6 | warm_empathetic:AFF:empathy_expression | UNDER | 0.100 | 0.100 | 14/14 under | 0.000 |
| 7 | anxious_hedger:MET:metacommentary | OVER | 0.096 | 0.090 | 14/14 over | 0.050 |
| 8 | anxious_hedger:AFF:emotion_word_density | OVER | 0.095 | 0.150 | 13/14 over | 0.025 |
| 9 | warm_empathetic:INT:question_frequency | OVER | 0.092 | 0.050 | 14/14 over | 0.000 |
| 10 | blunt_technical:PRA:humor_frequency | UNDER | 0.092 | 0.100 | 14/14 under | 0.000 |
| 11 | anxious_hedger:DSC:vulnerability_willingness | OVER | 0.088 | 0.050 | 14/14 over | 0.000 |
| 12 | warm_empathetic:PRA:directness | UNDER | 0.088 | 0.100 | 14/14 under | 0.025 |
| 13 | warm_empathetic:AFF:emotional_polarity_balance | UNDER | 0.086 | 0.070 | 10/14 under | 0.022 |
| 14 | casual_bro:PRA:humor_frequency | UNDER | 0.086 | 0.050 | 14/14 under | 0.000 |
| 15 | storyteller:SYN:sentence_length | OVER | 0.085 | 0.100 | 13/14 over | 0.025 |
| 16 | anxious_hedger:LEX:colloquialism | OVER | 0.082 | 0.025 | 11/14 over | 0.025 |
| 17 | formal_academic:LEX:jargon_density | OVER | 0.080 | 0.000 | 10/14 over | 0.025 |
| 18 | casual_bro:LEX:formality | OVER | 0.078 | 0.050 | 13/14 over | 0.000 |
| 19 | casual_bro:PRA:directness | UNDER | 0.076 | 0.050 | 13/14 under | 0.000 |
| 20 | casual_bro:LEX:hedging_frequency | OVER | 0.075 | 0.000 | 13/14 over | 0.025 |

### Top 5 Systematic Bias Features -- Deep Analysis and Proposed Solutions

#### #1: anxious_hedger:SYN:ellipsis_frequency (v2.7 error = 0.200, OVER)

**Problem:** Target is 0.60 but detector consistently reads 0.65-0.80. The speaker generates text with high ellipsis usage (the "..." pattern is natural for anxious speech), but the detector over-counts. This feature has been OVER in 14/14 versions -- the most consistent bias in the entire system.

**Trajectory:** Error has oscillated 0.05-0.20 but never reached zero. Even at best (v2.2 = 0.050), it rebounded to 0.200 in v2.7.

**Root cause hypothesis:** The anxious_hedger speaker generates multiple forms of trailing-off behavior (ellipsis, em-dashes, incomplete sentences) and the detector counts all of them as ellipsis. Additionally, the speaker may genuinely overuse literal "..." because the prompt associates anxiety with trailing off.

**Proposed solution:** **Both (Speaker + Detector)**
- **Speaker-side:** Calibrate the anxious_hedger prompt to explicitly constrain literal ellipsis usage while maintaining other hedging markers. Add negative examples: "Use ellipsis sparingly -- convey hesitation through word choice and sentence structure rather than punctuation."
- **Detector-side:** Tighten the ellipsis detection to count only literal "..." and not other trailing-off patterns. Normalize by text length to prevent longer anxious texts from inflating the count.

---

#### #2: anxious_hedger:AFF:emotion_word_density (v2.7 error = 0.150, OVER)

**Problem:** Target is 0.50 but detector reads 0.55-0.73 across versions. The anxious_hedger speaker generates emotionally-charged language as part of its anxious persona, and the detector reads this as higher emotion word density than intended.

**Trajectory:** Highly variable (0.017 to 0.233) but consistently OVER (13/14 versions). The error spiked in v1.8 (0.233) and v2.7 (0.150), suggesting prompt changes that amplified anxiety markers also amplified emotion words.

**Root cause hypothesis:** The distinction between "anxiety markers" and "emotion words" is blurry. Words like "worried," "concerned," "nervous," "afraid" are both anxiety indicators AND emotion words. The speaker cannot express anxiety without using emotion words.

**Proposed solution:** **Detector-side**
- Recalibrate the emotion_word_density detector to discount anxiety-specific vocabulary when analyzing the anxious_hedger profile. Consider a context-aware emotion lexicon that distinguishes between "functional anxiety markers" and "affective emotion words."
- Alternatively, adjust the target value upward from 0.50 to 0.55-0.60 to acknowledge that anxious speech inherently carries higher emotion density. This is a **profile target recalibration**.

---

#### #3: casual_bro:SYN:sentence_length (v2.7 error = 0.100, OVER)

**Problem:** Target is 0.15 (very short sentences) but detector consistently reads 0.25-0.30. The error has been OVER in 14/14 versions and never dropped below 0.100. This is the most stubbornly consistent bias -- the error range is only 0.050 (0.100-0.150), meaning it barely moves despite prompt changes.

**Trajectory:**
- v1.5-v2.1: Stuck at 0.117-0.150
- v2.2-v2.7: Improved slightly to 0.100
- v2.8: Regressed back to 0.150

**Root cause hypothesis:** LLMs have a natural sentence length floor. Even when instructed to write very short sentences, they produce sentences that are longer than the 0.15 target expects. The target of 0.15 may be below what an LLM can naturally produce for coherent conversational text. This is a structural limitation masquerading as systematic bias.

**Proposed solution:** **Architecture (Target Recalibration)**
- The target of 0.15 appears to be below the LLM's natural minimum. Conduct an empirical study: generate 100 casual_bro messages with maximum sentence-shortening instructions, measure the actual sentence length distribution, and set the target to the achievable minimum (likely 0.22-0.25).
- If the target must remain at 0.15, add **Speaker-side** reinforcement: explicit instructions like "Write in fragments. One to four words per line. Break every thought into its own sentence." combined with few-shot examples showing the exact target style.

---

#### #4: warm_empathetic:AFF:empathy_expression (v2.7 error = 0.100, UNDER)

**Problem:** Target is 0.95 (near-maximum empathy) but detector consistently reads 0.80-0.90. This feature has been UNDER in 14/14 versions and has a stability std of 0.000 -- meaning it is perfectly stable across repeated runs but stubbornly wrong. It is the definition of a systematic bias.

**Trajectory:**
- Best ever: v2.1 = 0.057 (detected 0.89), v2.6 = 0.050 (detected 0.90)
- v2.7 regressed to 0.100 (detected 0.85)
- The feature has touched 0.050 error twice but always rebounds

**Root cause hypothesis:** There is a ceiling effect. The detector's empathy_expression scale likely tops out around 0.85-0.90 for any realistic text, because the detector calibration was trained/designed with an implicit maximum that falls short of 0.95. The speaker may be producing maximally empathetic text, but the detector cannot score it above ~0.90.

**Proposed solution:** **Detector-side**
- Recalibrate the empathy_expression detector scale. Investigate what a "0.95 empathy" text looks like concretely and ensure the detector's rubric can distinguish between 0.85 and 0.95 levels. Current evidence suggests the detector compresses the top of the scale.
- Alternatively, recalibrate the target downward from 0.95 to 0.90, acknowledging the achievable ceiling. A target of 0.90 would yield near-zero error with current generation.

---

#### #5: blunt_technical:PRA:humor_frequency (v2.7 error = 0.100, UNDER)

**Problem:** Target is 0.10 (minimal humor) but detector reads 0.00 in 11/14 versions. The speaker generates text with zero detectable humor, and the detector confirms this -- but the target says there should be a small amount (0.10).

**Trajectory:** Error is 0.100 in 11 versions, 0.083 in one, and 0.050 in two (v1.9, v2.8). The detected value is almost always 0.00. This is perfectly stable (stab_std = 0.000).

**Root cause hypothesis:** The blunt_technical profile prompt produces text that is so dry and technical that any hint of humor is eliminated. The target of 0.10 implies "occasionally dry/subtle humor," but the LLM interprets "blunt technical communicator" as humorless. This is a semantic gap: the profile design intends minimal but nonzero humor, but the LLM and detector agree on zero.

**Proposed solution:** **Speaker-side**
- Add explicit humor instructions to the blunt_technical speaker prompt: "Occasionally use dry, deadpan technical humor -- for example, understated observations about obvious things, or ironic technical comparisons. Aim for one subtle joke per 3-4 exchanges."
- Include few-shot examples demonstrating blunt-but-humorous technical communication (e.g., "Well, that's what happens when you rm -rf your way to enlightenment.").

---

### Solution Classification Summary (Top 5)

| # | Feature | Solution Type | Confidence |
|---|---------|--------------|------------|
| 1 | anxious_hedger:SYN:ellipsis_frequency | **Both** (Speaker + Detector) | Medium -- requires coordinated calibration |
| 2 | anxious_hedger:AFF:emotion_word_density | **Detector-side** (or target recalibration) | High -- clear measurement conflation |
| 3 | casual_bro:SYN:sentence_length | **Architecture** (target recalibration) | High -- empirical minimum is above target |
| 4 | warm_empathetic:AFF:empathy_expression | **Detector-side** (scale recalibration) | High -- ceiling compression effect |
| 5 | blunt_technical:PRA:humor_frequency | **Speaker-side** | Medium -- semantic gap in prompt |

---

## Category 3: Structural Limitation Features

**Definition:** Features where the LLM fundamentally struggles to produce the target value because the target sits at an extreme (>0.85 or <0.15) or because the feature requires behaviors that conflict with the LLM's base tendencies. These differ from systematic bias in that no reasonable prompt or detector change can fully resolve them -- they reflect inherent LLM constraints.

### Features (23 total -- showing features with extreme targets)

| Feature | Mean Err | Target | Detected Range | Dir |
|---------|----------|--------|----------------|-----|
| warm_empathetic:AFF:empathy_expression | 0.100 | 0.95 | 0.80-0.90 | UNDER |
| casual_bro:SYN:sentence_length | 0.131 | 0.15 | 0.25-0.30 | OVER |
| casual_bro:LEX:formality | 0.078 | 0.05 | 0.10-0.15 | OVER |
| casual_bro:SYN:sentence_complexity | 0.050 | 0.10 | 0.13-0.15 | OVER |
| casual_bro:PRA:humor_frequency | 0.086 | 0.80 | 0.67-0.75 | UNDER |
| casual_bro:PRA:directness | 0.076 | 0.85 | 0.68-0.80 | UNDER |
| casual_bro:LEX:colloquialism | 0.054 | 0.95 | 0.85-0.95 | UNDER |
| warm_empathetic:PRA:politeness_strategy | 0.055 | 0.90 | 0.83-0.85 | UNDER |
| warm_empathetic:PRA:directness | 0.088 | 0.25 | 0.15-0.20 | UNDER |
| anxious_hedger:LEX:hedging_frequency | 0.061 | 0.95 | 0.88-0.90 | UNDER |
| formal_academic:PRA:humor_frequency | 0.050 | 0.05 | 0.00-0.05 | UNDER |
| blunt_technical:PRA:humor_frequency | 0.092 | 0.10 | 0.00-0.05 | UNDER |

### Interpretation

The structural limitations cluster into three sub-patterns:

1. **Ceiling compression (targets > 0.85):** The LLM generates text that is "very X" but the detector cannot distinguish between 0.85 and 0.95 levels of a feature. Examples: empathy_expression (0.95), hedging_frequency (0.95), colloquialism (0.95), politeness_strategy (0.90). The generated text is near-maximal, but the scale compresses at the top.

2. **Floor resistance (targets < 0.15):** The LLM cannot produce text below a natural minimum for certain features. Examples: sentence_length (0.15), formality (0.05), sentence_complexity (0.10). Even with aggressive prompt engineering, the LLM's outputs have inherent minimums for these syntactic features.

3. **Zero-point detection failure (targets near 0):** Features like humor_frequency at 0.05-0.10 targets struggle because the detector reads 0.00 -- it cannot detect the extremely subtle presence the target implies.

**Recommendation:** For ceiling and floor features, conduct empirical target recalibration. Measure what the LLM actually achieves at maximum/minimum effort and adjust targets to achievable ranges. This is not "lowering the bar" -- it is correctly calibrating the bar to the instrument.

---

## Category 4: Interaction-Caused Features

**Definition:** Features where fixing one problem caused another to regress, or where version changes create cascading effects across features within a profile or across profiles.

### v2.6 to v2.7 Regressions (despite overall MAE improvement)

v2.7 achieved the best overall MAE (0.0466), but 13 features regressed by 0.05+ from v2.6:

| Feature | v2.6 | v2.7 | Delta |
|---------|------|------|-------|
| anxious_hedger:AFF:emotional_volatility | 0.050 | 0.200 | +0.150 |
| anxious_hedger:SYN:ellipsis_frequency | 0.100 | 0.200 | +0.100 |
| anxious_hedger:AFF:emotion_word_density | 0.050 | 0.150 | +0.100 |
| blunt_technical:SYN:sentence_length | 0.050 | 0.150 | +0.100 |
| casual_bro:AFF:emotion_word_density | 0.050 | 0.150 | +0.100 |
| storyteller:SYN:sentence_length | 0.000 | 0.100 | +0.100 |
| warm_empathetic:AFF:empathy_expression | 0.050 | 0.100 | +0.050 |
| warm_empathetic:AFF:emotional_polarity_balance | 0.020 | 0.070 | +0.050 |
| casual_bro:PRA:directness | 0.000 | 0.050 | +0.050 |
| blunt_technical:LEX:jargon_density | 0.000 | 0.050 | +0.050 |
| blunt_technical:LEX:vocabulary_richness | 0.000 | 0.050 | +0.050 |
| storyteller:AFF:emotion_word_density | 0.050 | 0.100 | +0.050 |
| storyteller:DIS:example_frequency | 0.000 | 0.050 | +0.050 |

### v2.7 to v2.8 Regressions (attempted correction overcorrected)

v2.8 regressed overall MAE from 0.0466 to 0.0503. The following features got worse:

| Feature | v2.7 | v2.8 | Delta |
|---------|------|------|-------|
| warm_empathetic:DSC:vulnerability_willingness | 0.000 | 0.100 | +0.100 |
| anxious_hedger:LEX:formality | 0.000 | 0.100 | +0.100 |
| storyteller:PRA:humor_frequency | 0.050 | 0.150 | +0.100 |
| storyteller:MET:metacommentary | 0.040 | 0.110 | +0.070 |
| casual_bro:SYN:sentence_length | 0.100 | 0.150 | +0.050 |
| warm_empathetic:PRA:politeness_strategy | 0.050 | 0.100 | +0.050 |
| anxious_hedger:DSC:vulnerability_willingness | 0.050 | 0.100 | +0.050 |
| anxious_hedger:PRA:politeness_strategy | 0.000 | 0.050 | +0.050 |

### Interaction Patterns Identified

1. **Sentence length vs. everything else:** When prompt changes target sentence length (casual_bro, storyteller), they cascade into formality, vocabulary richness, and sentence complexity. Shorter sentences mechanically reduce complexity and shift formality detection.

2. **Anxiety cluster coupling:** In anxious_hedger, ellipsis_frequency, emotional_volatility, and emotion_word_density move together. Prompt changes that increase anxiety markers inflate all three simultaneously. They cannot be tuned independently.

3. **The v2.7/v2.8 whack-a-mole:** v2.8 attempted to fix v2.7's regressions but created new ones in different features. This is the classic symptom of an optimization surface with correlated features -- improving one pulls others off-target.

4. **Cross-profile sentence_length contagion:** v2.7 regressed sentence_length for blunt_technical (+0.100), storyteller (+0.100), and casual_bro stayed flat. This suggests a shared prompt component or detector change affected sentence_length measurement globally.

**Recommendation:** Features in this category require **coordinated multi-feature optimization** rather than single-feature fixes. Consider implementing a constraint-based optimization that simultaneously satisfies multiple feature targets, or accept that some features must be fixed at the expense of others and choose which to prioritize.

---

## Special Focus Sections

### Focus: anxious_hedger (Worst Profile)

anxious_hedger is the worst-performing profile across all versions. Its MAE has ranged from 0.049 (v2.0 -- the only time it dipped below 0.06) to 0.088 (v1.5), and at v2.7 it sits at 0.076 -- nearly double the formal_academic MAE of 0.027.

**Feature-by-feature breakdown at v2.7:**

| Feature | Error | Dir | Mean Across All | Category |
|---------|-------|-----|-----------------|----------|
| SYN:ellipsis_frequency | 0.200 | OVER | 0.145 | Systematic Bias |
| AFF:emotional_volatility | 0.200 | FLIP | 0.075 | Noise |
| AFF:emotion_word_density | 0.150 | OVER | 0.095 | Systematic Bias |
| LEX:hedging_frequency | 0.100 | UNDER | 0.061 | Structural Limit |
| MET:metacommentary | 0.090 | OVER | 0.096 | Systematic Bias |
| DSC:vulnerability_willingness | 0.050 | OVER | 0.088 | Systematic Bias |
| PRA:directness | 0.050 | FLIP | 0.031 | Noise |
| MET:self_correction_frequency | 0.050 | FLIP | 0.030 | Noise |
| LEX:colloquialism | 0.025 | OVER | 0.082 | Systematic Bias |
| PTX:expressive_punctuation | 0.000 | -- | 0.052 | Noise |
| LEX:formality | 0.000 | -- | 0.062 | Systematic Bias |
| PRA:politeness_strategy | 0.000 | -- | 0.055 | Systematic Bias |

**Why anxious_hedger is hard:**

1. **Feature coupling:** The anxious persona creates a cluster of correlated behaviors (ellipsis, emotion words, metacommentary, vulnerability) that the speaker amplifies together. Reducing one reduces them all.
2. **Extreme behavior targets:** Several targets ask for behaviors (high ellipsis at 0.60, high hedging at 0.95, high vulnerability at 0.70) that the LLM tends to overshoot because the "anxious" instruction gets interpreted as "maximally anxious."
3. **Volatility is intrinsically noisy:** Emotional volatility requires varied emotional expression across a text, which is inherently stochastic. The v2.5 stability std of 0.037 means this feature changes by ~4 points between identical runs.

**Recommended intervention:** A dedicated anxious_hedger prompt rewrite that:
- Decouples anxiety markers from each other with explicit constraints ("Use hedging words frequently but limit literal ellipsis to 2-3 per message")
- Provides calibrated examples showing the target anxiety level (moderate, not extreme)
- Reduces metacommentary by redirecting self-awareness into hedge words rather than explicit meta-statements

### Focus: casual_bro:SYN:sentence_length

**The immovable feature.** Target = 0.15, detected range = 0.25-0.30, error range = 0.100-0.150, OVER in 14/14 versions.

| Version | Error | Detected |
|---------|-------|----------|
| v1.5 | 0.150 | 0.30 |
| v1.6 | 0.117 | 0.27 |
| v1.7 | 0.133 | 0.28 |
| v2.2 | 0.100 | 0.25 |
| v2.5-v2.7 | 0.100 | 0.25 |
| v2.8 | 0.150 | 0.30 |

This feature has the narrowest error range of any high-error feature (only 0.050 spread). The detected value oscillates between exactly 0.25 and 0.30 -- never lower, never higher. This is the clearest evidence of an **LLM floor effect**: the model physically cannot produce coherent casual text with sentence lengths at the 0.15 level. The 0.25 floor is the shortest sentences the LLM can reliably produce for this style.

**Verdict:** Recalibrate target to 0.25. Attempting to push below this wastes optimization effort and creates regressions in other features.

### Focus: warm_empathetic:AFF:empathy_expression

**The ceiling feature.** Target = 0.95, detected range = 0.80-0.90, UNDER in 14/14 versions, stability std = 0.000.

This is the most perfectly stable systematic bias in the entire system. Across 4 repeated v2.5 runs, the error is identical. The detected value clusters at 0.85 (+/-0.05), never reaching the 0.95 target.

The stability std of 0.000 means this is not a generation problem -- the speaker produces consistently empathetic text. The issue is either:
1. The detector's empathy scale is compressed above 0.85, or
2. The target of 0.95 is above what any realistic text achieves on this scale

**Verdict:** Detector recalibration. Examine whether the empathy_expression rubric has sufficient gradations above 0.85 to distinguish 0.85 from 0.95 text.

### Focus: blunt_technical:LEX:formality

**The volatile bias.** Mean error = 0.113, but error range = 0.230 (from 0.020 to 0.250). Stability std = 0.098 -- the highest of any feature in the system.

| Version | Error | Detected | Dir |
|---------|-------|----------|-----|
| v1.5 | 0.250 | 0.85 | OVER |
| v2.1 | 0.037 | 0.56 | UNDER |
| v2.3 | 0.020 | 0.58 | UNDER |
| v2.5 | 0.070 | 0.53 | UNDER |
| v2.7 | 0.030 | 0.63 | OVER |
| v2.8 | 0.070 | 0.53 | UNDER |

This feature is remarkable: it has a systematic bias (OVER in 10/14 versions, mean error 0.113) but also extreme volatility. The detected value ranges from 0.53 to 0.85 across versions, and even across v2.5 stability runs the std is 0.098.

**Root cause:** The "blunt technical" style sits at a formality level (0.60) that is ambiguous. Technical writing can be either very formal (academic-style) or informal (Stack Overflow-style). Different LLM generation runs produce dramatically different formality levels depending on which "technical" archetype the model anchors to.

**Recommended intervention:**
- **Speaker-side:** Pin the formality level explicitly: "Write at moderate formality -- not academic, not casual. Think senior engineer explaining to a peer. No slang, no jargon-free simplification, but also no passive voice or hedge words."
- **Detector-side:** Investigate why the formality detector produces such different readings for presumably similar text. The within-run std of 0.136 (across 3 samples per run) suggests the generated texts vary substantially.

---

## Near-Perfect Features (9 total)

These features consistently achieve mean error < 0.02 and should be preserved as-is:

| Feature | Mean Error | Stability Std |
|---------|-----------|---------------|
| formal_academic:PTX:emoji_usage | 0.000 | 0.000 |
| formal_academic:ERR:grammar_deviation | 0.000 | 0.000 |
| blunt_technical:PTX:emoji_usage | 0.000 | 0.000 |
| blunt_technical:AFF:emotion_word_density | 0.006 | 0.033 |
| warm_empathetic:LEX:formality | 0.007 | 0.025 |
| storyteller:INT:response_elaboration | 0.007 | 0.000 |
| formal_academic:LEX:formality | 0.009 | 0.000 |
| warm_empathetic:DSC:vulnerability_willingness | 0.014 | 0.000 |
| blunt_technical:PRA:directness | 0.014 | 0.000 |

**Pattern:** Near-perfect features tend to be either binary/extreme (emoji_usage at 0.00, grammar_deviation at 0.00) or features where the target naturally matches the LLM's default for that profile. These require no intervention and should be monitored for regressions only.

---

## Strategic Recommendations

### Highest-Impact Next Steps (Ordered by Expected MAE Reduction)

1. **Target recalibration for structural limitations** -- Adjust 4-6 targets that sit beyond the LLM's achievable range (casual_bro:sentence_length 0.15->0.25, warm_empathetic:empathy_expression 0.95->0.90, etc.). Expected MAE impact: -0.005 to -0.008 across the board.

2. **anxious_hedger dedicated prompt rewrite** -- This single profile contributes disproportionately to overall MAE. A coordinated rewrite addressing feature coupling could reduce anxious_hedger MAE from 0.076 to 0.050-0.060. Expected overall MAE impact: -0.003 to -0.004.

3. **Detector recalibration for empathy_expression and humor_frequency** -- Both have zero stability variance and consistent bias, meaning detector adjustment directly translates to error reduction. Expected impact: -0.002 per feature.

4. **Multi-run averaging at eval time** -- For Category 1 (noise) features, average 3-5 runs instead of using single runs. This would reduce noise-floor contribution to MAE by approximately sqrt(n). Expected impact: -0.002 to -0.003.

5. **Accept the noise floor** -- Stop attempting to optimize Category 1 features individually. The current noise floor of ~0.02-0.03 MAE from stochastic variation is the cost of using LLMs for text generation and cannot be reduced through prompt engineering.

### Achievable Target

With target recalibration + anxious_hedger rewrite + detector fixes, an overall MAE of **0.035-0.040** appears achievable. Below 0.035 would require either architectural changes (multi-run generation with selection) or acceptance that the remaining error is irreducible.
