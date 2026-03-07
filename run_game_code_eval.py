#!/usr/bin/env python3
"""PDCA iteration runner for Wireframe→GameCode pipeline (Stage 4).

Usage:
    ANTHROPIC_API_KEY=... python run_game_code_eval.py [--game flappy_bird|snake|tetris] \
        [--semantic] [--best-of-n 3]
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from intention_graph.game_code_generator import GameCodeGenerator
from intention_graph.game_code_quality import evaluate, semantic_evaluate
from intention_graph.game_code_browser_test import browser_smoke_test

GOLDEN_DIR = os.path.join(
    os.path.dirname(__file__),
    "intention_graph", "golden_samples",
)

GAMES = {
    "flappy_bird": "Flappy Bird",
    "snake": "Snake",
    "tetris": "Tetris",
    "2048": "2048",
    "breakout": "Breakout",
    "match3": "Match 3",
    "minesweeper": "Minesweeper",
    "space_shooter": "Space Shooter",
}


def load_golden(game: str) -> tuple[dict | None, str]:
    """Load golden wireframe and PRD source for a game."""
    game_dir = os.path.join(GOLDEN_DIR, game)
    wf_path = os.path.join(game_dir, "wireframe.json")
    src_path = os.path.join(game_dir, "source.md")

    wireframe = None
    prd = ""

    if os.path.exists(wf_path):
        with open(wf_path) as f:
            wireframe = json.load(f)
    if os.path.exists(src_path):
        with open(src_path) as f:
            prd = f.read()

    return wireframe, prd


def run_game_code_eval(
    game: str = "flappy_bird",
    api_key: str = "",
    with_semantic: bool = False,
    with_browser: bool = False,
    best_of_n: int = 1,
) -> dict:
    """Run full Stage 4 PDCA pipeline and return metrics."""
    api_key = api_key or os.environ["ANTHROPIC_API_KEY"]
    wireframe, prd_doc = load_golden(game)

    if not wireframe:
        print(f"ERROR: No wireframe.json found for {game}")
        return {"game": game, "error": "no wireframe"}

    if not prd_doc:
        prd_doc = f"Create a {GAMES.get(game, game)} game."

    t0 = time.time()
    results: dict = {"game": game, "stages": {}}

    print(f"\n{'=' * 60}")
    print(f"GAME CODE EVAL: {game}")
    print(f"{'=' * 60}")

    # Wireframe info
    wf_screens = wireframe.get("interfaces", [])
    total_elems = sum(len(s.get("elements", [])) for s in wf_screens)
    print(f"[Wireframe] {len(wf_screens)} screens, {total_elems} elements")
    for s in wf_screens:
        print(f"  [{s.get('interface_id', '?')}] "
              f"{len(s.get('elements', []))} elements, "
              f"nav→{s.get('children', [])}")
    results["stages"]["wireframe"] = {
        "screen_count": len(wf_screens),
        "total_elements": total_elems,
    }

    # Generate game code
    print(f"\n--- Generating code (best-of-{best_of_n}) ---")
    gen = GameCodeGenerator(api_key=api_key)

    if best_of_n > 1:
        code, gen_score = gen.generate_best_of_n(
            prd_doc, wireframe, n=best_of_n,
        )
        print(f"[Generate] Best-of-{best_of_n} selected (score={gen_score:.0%})")
    else:
        code = gen.generate(prd_doc, wireframe)
        print(f"[Generate] Single candidate")

    results["stages"]["code"] = {
        "html_chars": len(code.get("index.html", "")),
        "css_chars": len(code.get("style.css", "")),
        "js_chars": len(code.get("core.js", "")),
    }
    print(f"[Code] HTML={len(code.get('index.html', ''))} chars, "
          f"CSS={len(code.get('style.css', ''))} chars, "
          f"JS={len(code.get('core.js', ''))} chars")

    # Layer 1+2 Evaluation
    print(f"\n--- Evaluation ---")
    report = evaluate(
        code.get("index.html", ""),
        code.get("style.css", ""),
        code.get("core.js", ""),
        wireframe,
    )

    print(f"\n  Structural: {report.overall_score:.0%} "
          f"({'PASS' if report.passed else 'FAIL'}, "
          f"{len(report.failures)} failures)")
    for m in report.metrics:
        status = "PASS" if m.passed else "FAIL"
        print(f"    [{status}] {m.name}: {m.score:.0%} — {m.detail}")

    results["structural"] = {
        "overall": report.overall_score,
        "passed": report.passed,
        "failures": len(report.failures),
        "metrics": {m.name: m.score for m in report.metrics},
    }

    # Layer 3: Semantic evaluation (optional)
    if with_semantic:
        print(f"\n--- Semantic Evaluation ---")
        sem = semantic_evaluate(
            code.get("index.html", ""),
            code.get("style.css", ""),
            code.get("core.js", ""),
            wireframe,
            prd_doc,
            api_key,
        )
        print(f"  Semantic: {sem.score:.0%} "
              f"{'PASS' if sem.passed else 'FAIL'} — {sem.detail}")
        results["semantic"] = {"score": sem.score, "detail": sem.detail}

    # Layer 4: Browser smoke test (optional)
    if with_browser:
        print(f"\n--- Browser Smoke Test ---")
        browser_result = browser_smoke_test(
            code.get("index.html", ""),
            code.get("style.css", ""),
            code.get("core.js", ""),
            wireframe,
        )
        print(f"  Browser: {browser_result.score:.0%} "
              f"{'PASS' if browser_result.passed else 'FAIL'} — {browser_result.detail}")
        results["browser"] = {
            "score": browser_result.score,
            "passed": browser_result.passed,
            "detail": browser_result.detail,
        }

    # Save generated files
    output_dir = os.path.join(os.path.dirname(__file__), "output", game)
    os.makedirs(output_dir, exist_ok=True)
    for filename, content in code.items():
        with open(os.path.join(output_dir, filename), "w") as f:
            f.write(content)
    print(f"\n  Output saved to {output_dir}/")

    elapsed = time.time() - t0
    results["elapsed_sec"] = round(elapsed, 1)
    print(f"\nDone in {elapsed:.1f}s")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Game Code PDCA Evaluation Runner")
    parser.add_argument(
        "--game", default="flappy_bird",
        choices=list(GAMES.keys()) + ["all"],
        help="Game to evaluate",
    )
    parser.add_argument("--semantic", action="store_true", help="Run Layer 3 LLM judge")
    parser.add_argument("--browser", action="store_true", help="Run Playwright browser smoke tests")
    parser.add_argument("--best-of-n", type=int, default=1, help="Generate N candidates")
    args = parser.parse_args()

    if args.game == "all":
        all_results = {}
        for g in GAMES:
            try:
                r = run_game_code_eval(
                    game=g,
                    with_semantic=args.semantic,
                    with_browser=args.browser,
                    best_of_n=args.best_of_n,
                )
                all_results[g] = r
            except Exception as e:
                print(f"\nERROR on {g}: {e}")
                all_results[g] = {"game": g, "error": str(e)}

        print(f"\n{'=' * 60}")
        print("CROSS-GAME SUMMARY")
        print(f"{'=' * 60}")
        for g, r in all_results.items():
            if "error" in r:
                print(f"  {g:16s}: ERROR — {r['error']}")
                continue
            structural = r.get("structural", {}).get("overall", 0)
            failures = r.get("structural", {}).get("failures", "?")
            elapsed = r.get("elapsed_sec", "?")
            print(f"  {g:16s}: {structural:.0%} "
                  f"({failures} failures) "
                  f"time={elapsed}s")
    else:
        run_game_code_eval(
            game=args.game,
            with_semantic=args.semantic,
            with_browser=args.browser,
            best_of_n=args.best_of_n,
        )
