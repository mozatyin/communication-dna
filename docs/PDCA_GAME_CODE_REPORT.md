# PDCA Game Code Report — Stage 4 (Wireframe → HTML/CSS/JS)

**Date:** 2026-03-07
**Pipeline:** PRD → InterfacePlan → Assets → Wireframe → **GameCode**
**Evaluator:** `game_code_quality.py` (Layer 1+2+3)
**Generator:** `game_code_generator.py` (claude-sonnet via OpenRouter)

## Summary

| Game | Overall | Failures | L1 Avg | L2 Avg | Time |
|------|---------|----------|--------|--------|------|
| Flappy Bird | **84%** | 0 | 100% | 79% | 58s |
| Snake | **91%** | 0 | 98% | 84% | 58s |
| Tetris | **90%** | 0 | 96% | 85% | 80s |

**All 3 games pass** on first attempt (single candidate, no best-of-N needed).

## Layer 1: Code Runnability (100% pass rate)

All 3 games score perfectly on code structure:

| Metric | Flappy | Snake | Tetris |
|--------|--------|-------|--------|
| file_completeness | 100% | 100% | 100% |
| html_validity | 100% | 100% | 100% |
| js_syntax | 100% | 100% | 100% |
| css_reference_integrity | 57% | 90% | 82% |

**Finding:** `css_reference_integrity` is the weakest L1 metric (57-90%). The generator creates HTML IDs/classes that don't all have matching CSS rules. This is acceptable — many elements are styled via parent selectors or canvas rendering.

## Layer 2: Wireframe Fidelity (all pass, room for improvement)

| Metric | Flappy | Snake | Tetris |
|--------|--------|-------|--------|
| screen_coverage | 100% | 100% | 100% |
| element_coverage | 67% | 81% | 86% |
| style_fidelity | 50% | 54% | 53% |
| navigation_integrity | 100% | 100% | 100% |

**Key patterns:**

1. **Screen coverage: 100%** — Generator perfectly maps every wireframe `interface_id` to a `<div id="..." class="screen">`. This is the strongest metric.

2. **Navigation integrity: 100%** — All wireframe navigation edges (button→target) have corresponding JS handlers. The `showScreen()` pattern works reliably.

3. **Element coverage: 67-86%** — Gameplay screens tend to under-count HTML elements because wireframe image assets (pipes, bird, etc.) are rendered on canvas instead of as DOM elements. This is actually correct behavior for games.

4. **Style fidelity: 50-54%** — Weakest metric. About half of wireframe colors/font-sizes appear verbatim in CSS. Common misses:
   - Font sizes specified in wireframe (e.g., `"36px"`) sometimes rendered differently
   - Colors from wireframe background images don't map to CSS (they're canvas-drawn)

## Layer 3: Semantic Evaluation (Flappy Bird sample)

| Dimension | Score |
|-----------|-------|
| mechanics_completeness | 8/10 |
| state_management | 7/10 |
| interaction_quality | 8/10 |
| **Combined** | **77% PASS** |

**LLM judge issues identified:**
- Game loop references incomplete rendering functions
- Canvas drawing logic for bird/pipes partially missing
- Leaderboard shows static data instead of dynamic scores
- Paused state defined but unused

## Failure Pattern Analysis

### Pattern 1: Canvas vs DOM element counting
**Impact:** element_coverage metric undervalues canvas-based games
**Root cause:** Wireframe specifies individual image elements (bird, pipes) that become canvas sprites, not DOM elements
**Recommendation:** Add canvas-awareness to element_coverage — detect `<canvas>` and give credit for canvas-rendered elements

### Pattern 2: Style value normalization
**Impact:** style_fidelity at ~50%
**Root cause:** Wireframe uses format like `"24px"` or `"#E8A43A"` but CSS may use `1.5rem` or `rgb()` equivalents
**Recommendation:** Expand color normalization (hex↔rgb) and size normalization (px↔rem)

### Pattern 3: Incomplete game mechanics
**Impact:** Semantic score 77% — playable but not complete
**Root cause:** Single-shot generation tries to fit full game logic in one response; complex games need more JS
**Recommendation:** For PDCA iteration, use best-of-3 and iterate on the system prompt to require complete game loops

## Generated File Sizes

| Game | HTML | CSS | JS | Total |
|------|------|-----|----|-------|
| Flappy Bird | 2.0KB | 5.0KB | 8.2KB | 15.2KB |
| Snake | 1.8KB | 6.6KB | 7.5KB | 15.9KB |
| Tetris | 2.3KB | 7.7KB | 11.3KB | 21.3KB |

Tetris generates the most JS (11KB) due to piece rotation and line-clearing logic.

---

## Cycle 2: Post-Improvement Re-evaluation

**Date:** 2026-03-07
**Changes applied:** P0 (JS summary for semantic eval), P1 (canvas-aware element coverage), P2 (Playwright browser smoke tests), P3 (generator prompt completeness requirements)
**Config:** `--best-of-n 3 --semantic --browser`

### Cycle 2 Summary

| Game | Structural | Semantic | Browser | Time |
|------|-----------|----------|---------|------|
| Flappy Bird | **93%** (was 84%) | **87%** (was 77%) | **80%** (new) | 181s |
| Snake | **94%** (was 91%) | **83%** (new) | **100%** (new) | 172s |
| Tetris | **97%** (was 90%) | **80%** (new) | **100%** (new) | 251s |

### Before/After Comparison

| Metric | Cycle 1 Avg | Cycle 2 Avg | Delta |
|--------|------------|------------|-------|
| Structural overall | 88% | **95%** | +7% |
| element_coverage | 78% | **82%** | +4% |
| style_fidelity | 52% | **100%** | +48% |
| css_reference_integrity | 76% | **75%** | -1% |
| Semantic combined | 77%* | **83%** | +6% |
| Browser smoke | N/A | **93%** | new |

*Cycle 1 semantic was only measured for Flappy Bird.

### Cycle 2 Detailed Structural Metrics

| Metric | Flappy | Snake | Tetris |
|--------|--------|-------|--------|
| file_completeness | 100% | 100% | 100% |
| html_validity | 100% | 100% | 100% |
| js_syntax | 100% | 100% | 100% |
| css_reference_integrity | 59% | 75% | 91% |
| screen_coverage | 100% | 100% | 100% |
| element_coverage | 84% | 76% | 85% |
| style_fidelity | 100% | 100% | 100% |
| navigation_integrity | 100% | 100% | 100% |

### Key Improvements

1. **Style fidelity: 52% → 100%** — Biggest gain. The improved generator prompt with explicit style requirements eliminated all style mismatches.

2. **Element coverage: 78% → 82%** — Canvas-aware counting (P1) adds credit for canvas-rendered sprites. The gameplay screen now correctly counts fillStyle/drawImage calls as visual elements.

3. **Semantic eval: 77% → 83%** — JS structural summary (P0) eliminates false negatives from truncation. The LLM judge now sees function signatures, canvas calls, and event listeners instead of cut-off raw JS.

4. **Browser smoke: 93% avg** — New metric confirms games actually load and render in a real browser. Flappy Bird scored 80% (navigation_works=FAIL — button uses `startGame()` instead of `showScreen()` directly). Snake and Tetris score 100%.

### Remaining Issues

1. **Flappy Bird navigation_works: FAIL** — The Play button calls `startGame()` which internally calls `showScreen()`. The browser test only detects `onclick="showScreen(...)"` patterns. This is a test heuristic limitation, not a real bug.

2. **Element coverage still ~82%** — Gameplay screens show slight over-generation penalty. The canvas counting adds elements but some screens also have extra DOM elements beyond the wireframe spec.

3. **Semantic issues** are now more nuanced — the LLM judge notes missing details in the summary rather than the code itself (e.g., "Snake collision detection not visible in summary"). This suggests the summary could include more body context.

---

## Cycle 3: JS Summary Depth + Browser Nav Fix + 8-Game Expansion

**Date:** 2026-03-07
**Changes applied:** (1) Key game functions get 8 lines of body in JS summary instead of 2, (2) browser nav test clicks any button and checks screen visibility change, (3) click timeout guard prevents Playwright hangs
**Config:** `--best-of-n 3 --semantic --browser`

### Cycle 3 Summary — All 8 Games

| Game | Structural | Semantic | Browser | Time |
|------|-----------|----------|---------|------|
| Flappy Bird | **93%** | **87%** | 80%* | 168s |
| Snake | **96%** | **80%** | **100%** | 173s |
| Tetris | **91%** | **80%** | **100%** | 265s |
| 2048 | **98%** | **83%** | 80%* | — |
| Breakout | **89%** | **70%** | **100%** | — |
| Match 3 | **90%** | **70%** | **100%** | — |
| Minesweeper | **90%** | **87%** | **100%** | — |
| Space Shooter | **96%** | **70%** | 80%* | 201s |
| **Average** | **93%** | **78%** | **93%** | — |

*80% = navigation_works=FAIL due to buttons using addEventListener instead of onclick. Code fix applied but not re-run.

**All 8 games pass structural eval (0 failures). All 8 pass semantic eval (>=0.6).**

### Cross-Cycle Comparison (3 original games)

| Metric | C1 | C2 | C3 | Trend |
|--------|----|----|-----|-------|
| Structural avg | 88% | 95% | 93% | stable |
| Semantic avg | 77%* | 83% | 82% | stable |
| Browser avg | — | 93% | 93% | stable |
| element_coverage | 78% | 82% | 84% | +6 |
| style_fidelity | 52% | 100% | 84% | varies |

*C1 semantic measured on Flappy Bird only.

### Findings from 8-Game Expansion

**1. Style fidelity is game-dependent.** The 3 original games (with PRD source docs) score 84% avg style fidelity. The 5 new games (generic PRD) score 63% avg. Having a detailed PRD significantly improves style adherence.

**2. Semantic scores cluster by game complexity:**
- Simple mechanics (Minesweeper, Flappy Bird, 2048): 83-87%
- Medium (Snake, Tetris): 80%
- Complex (Breakout, Match3, Space Shooter): 70%

The 70% games all share the same issue: collision/interaction logic is too complex for the LLM judge to verify from a function summary alone.

**3. Browser smoke tests are robust.** 5/8 games score 100%. The 3 failures are all `navigation_works=FAIL` from the same root cause (buttons without onclick attributes). Fixed in code but not re-run.

**4. Structural scores are consistently high (89-98%).** The generator reliably produces valid HTML/CSS/JS with correct screen structure and navigation. This is a solved problem.

### Remaining Issues

1. **Semantic eval is the ceiling.** For complex games, the 70% score reflects real missing mechanics (animations, collision physics, difficulty progression) — not evaluator limitations. Improving this requires better code generation, not better evaluation.

2. **Style fidelity depends on PRD quality.** Games without detailed PRDs miss more style values. This is expected — the generator can only match styles it's told about.

3. **Leaderboard is universally static.** All 8 games have hardcoded leaderboard data. This is a systematic generator limitation.

## Next Steps (PDCA Cycle 4)

1. **Leaderboard persistence:** Add localStorage score saving requirement to generator prompt
2. **Complex game mechanics:** Consider multi-turn generation for Breakout/Match3/Space Shooter
3. **PRD generation for remaining 5 games:** Generate proper PRDs to improve style fidelity
4. **Semantic eval calibration:** For 70% games, verify whether issues are real or summary artifacts by manual code review
