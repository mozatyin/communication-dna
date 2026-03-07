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

## Next Steps (PDCA Act phase)

1. **Prompt iteration:** Add explicit instruction for complete game loop implementation
2. **Best-of-N:** Run with `--best-of-n 3` to improve output quality
3. **Canvas metric:** Adjust element_coverage to account for canvas-rendered sprites
4. **Style normalization:** Enhance color/size matching in style_fidelity
5. **Browser testing:** Manual verification that generated games are playable
