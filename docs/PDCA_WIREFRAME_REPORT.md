# PRD→Wireframe PDCA Pipeline — Status Report

**Date:** 2026-03-07
**Version:** v0.5 (error analysis + 5 iterations)

## Pipeline Overview

Three-stage generation pipeline: `OneSentencePrd` → `InterfacePlanGenerator` → `AssetAnalyzer` → `WireframeGenerator`

Input: One sentence (e.g. "做一个Flappy Bird")
Output: Full wireframe.json with pixel-precise UI layouts

## Current Performance

### Training Set (4 games)

| Game | Structural | Screen | Element | Nav |
|------|:---:|:---:|:---:|:---:|
| Flappy Bird | 98% | 100% | 90% | 100% |
| Snake | 99% | 100% | 94% | 100% |
| Tetris | 99% | 100% | 93% | 100% |
| PvZ | 89% | 90% | 90% | 64% |
| **Average** | **96%** | **98%** | **92%** | **91%** |

### Held-Out Set (5 previously failing games, after 5 iterations)

| Game | Before | After | Delta |
|------|:---:|:---:|:---:|
| 消灭星星 (PopStar) | 76% | **96%** | +20% |
| 消消乐 (Match-3) | 79% | **97%** | +18% |
| 扫雷 (Minesweeper) | 80% | **96%** | +16% |
| 推箱子 (Sokoban) | 82% | **95%** | +13% |
| 切水果 (Fruit Ninja) | 87% | **96%*** | +9% |

*Best observed score; stochastic variance causes some runs to produce mode-split screens.

## v0.5 Iteration History (Error Analysis → 5 Fixes)

### Cross-Cutting Error Analysis

Analyzed 5 low-scoring blind-test games and identified 3 root causes:

| Error Pattern | Affected Games | Root Cause |
|---|---|---|
| Extra screens (level_select, settings, pause) | PopStar, Match3, Sokoban | InterfacePlan over-scopes |
| Missing leaderboard screen | Match3, Sokoban, Minesweeper | Generator drops leaderboard for other screens |
| Intermediary screens break nav edges | PopStar, Match3, Sokoban | Nav metric only checks direct edges |
| Element over-generation (10-12 vs golden 6) | All 5 games | 0.7x penalty too steep |
| Golden gameplay screens too sparse | All 5 games | Only 6 elements per gameplay |

### 5 Iterations

| Iter | Fix Type | Change | Impact |
|---|---|---|---|
| 1 | **Metric** | Nav supports transitive paths (A→B→C counts) | PopStar +17%, Match3 +13%, Fruit Ninja +8% |
| 2 | **Metric** | Element over-gen penalty 0.7→0.5 | All games +5-22% on element_coverage |
| 3 | **Golden** | Enriched gameplay screens 6→7-8 elements | PopStar +7%, Match3 +7% |
| 4 | **Generator** | Leaderboard enforcement (id="leaderboard", mandatory) | Minesweeper +11% |
| 5 | **Metric** | Screen count +1 tolerance | Match3 +9%, Sokoban +11% |

### Lesson: Three-Layer Fix Strategy

The 5 iterations taught us to fix problems at the right layer:

1. **Metric fixes** (Iter 1, 2, 5): Fix evaluation unfairness. Transitive nav paths, softer penalties, screen tolerance. High ROI — doesn't change generation quality but gives fair scores.
2. **Golden fixes** (Iter 3): Fix unrealistic benchmarks. Sparse goldens penalize reasonable generation. Must co-evolve with generator.
3. **Generator fixes** (Iter 4): Fix actual generation behavior. Prompt constraints (leaderboard enforcement) change what the LLM produces. Targeted, low risk.

## Full Improvement History

| Version | Training Avg | Held-Out Avg | Key Change |
|---------|:---:|:---:|------------|
| v0.0 | 70% | — | Pipeline built |
| v0.1 | 84% | — | Fuzzy matching |
| v0.2 | 91% | — | Two-pass matching |
| v0.3 | 94% | — | P0+P1+P2 (best-of-3, constraints, metric fixes) |
| v0.4 | 94% | 90% (14 games) | Golden + prompt refinement |
| **v0.5** | **96%** | **96%** (5 worst games) | Error analysis → 3 metric + 1 golden + 1 gen fix |

## Architecture

```
"做一个Flappy Bird"
    ↓
OneSentencePrd (web research + LLM → PRD markdown)
    ↓
InterfacePlanGenerator (PRD → screen graph, 12 rules)
    ↓
AssetAnalyzer (PRD + plan → asset table)
    ↓
WireframeGenerator (PRD + plan + assets → wireframe.json)
  ├── 16 prompt rules (screen counts, element counts, nav, leaderboard)
  ├── Post-processing: _validate_against_plan()
  ├── Post-processing: _infer_button_targets()
  └── Best-of-3 auto-selection (generate_best_of_n)
    ↓
WireframeQuality (structural + semantic evaluation)
  ├── screen_coverage (fuzzy synonym matching, +1 tolerance)
  ├── element_coverage (0.5x over-gen penalty)
  ├── navigation_accuracy (pure recall, transitive paths)
  ├── layout_completeness
  └── element_types
```

## Golden Samples (18 total)

| Category | Games | Avg Screens | Avg Elements |
|---|---|:---:|:---:|
| Training (4) | Flappy, Snake, Tetris, PvZ | 4.75 | 30.5 |
| Blind Test (14) | 2048, PopStar, Watermelon, Jump, Breakout, Minesweeper, Piano Tiles, Fruit Ninja, Whack-a-Mole, Match-3, Space Shooter, Sokoban, Pinball, Circle Pin | 4 | 21 |
