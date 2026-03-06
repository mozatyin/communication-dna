#!/usr/bin/env python3
"""PDCA iteration runner for PRD→Wireframe pipeline.

Usage:
    ANTHROPIC_API_KEY=... python run_pdca.py [--game flappy|pvz] [--with-golden] [--semantic]
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from intention_graph.one_sentence_prd import OneSentencePrd
from intention_graph.interface_plan_generator import InterfacePlanGenerator
from intention_graph.asset_analyzer import AssetAnalyzer
from intention_graph.wireframe_generator import WireframeGenerator
from intention_graph.wireframe_quality import (
    evaluate,
    semantic_evaluate,
    _check_layout_completeness,
    _check_element_types,
)

GAMES = {
    "flappy": "做一个Flappy Bird",
    "pvz": "做一个植物大战僵尸",
    "tetris": "做一个俄罗斯方块",
    "snake": "做一个贪吃蛇",
}

GOLDEN_DIR = os.path.join(
    os.path.dirname(__file__),
    "intention_graph", "golden_samples",
)


def load_golden(game: str) -> tuple[dict | None, dict | None]:
    """Load golden interface_plan and wireframe if available."""
    game_dir = os.path.join(GOLDEN_DIR, game)
    plan_path = os.path.join(game_dir, "interface_plan.json")
    wf_path = os.path.join(game_dir, "wireframe.json")

    plan = None
    wf = None
    if os.path.exists(plan_path):
        with open(plan_path) as f:
            plan = json.load(f)
    if os.path.exists(wf_path):
        with open(wf_path) as f:
            wf = json.load(f)
    return plan, wf


def run_pdca(
    game: str = "flappy",
    api_key: str = "",
    with_golden: bool = False,
    with_semantic: bool = False,
) -> dict:
    """Run full PDCA pipeline and return metrics."""
    api_key = api_key or os.environ["ANTHROPIC_API_KEY"]
    prompt = GAMES.get(game, game)

    game_to_dir = {"flappy": "flappy_bird", "pvz": "pvz", "tetris": "tetris", "snake": "snake"}
    golden_plan, golden_wf = load_golden(game_to_dir.get(game, game))

    t0 = time.time()
    results = {"game": game, "stages": {}}

    # Stage 0: PRD
    print(f"\n{'='*60}")
    print(f"PDCA: {game} | golden={'yes' if golden_wf else 'no'}")
    print(f"{'='*60}")

    prd = OneSentencePrd(api_key=api_key).generate(prompt)
    prd_doc = prd["prd_document"]
    results["stages"]["prd"] = {
        "chars": len(prd_doc),
        "complexity": prd["metadata"].get("complexity", "?"),
    }
    print(f"[PRD] {len(prd_doc)} chars, {prd['metadata'].get('complexity', '?')}")

    # Stage 1: Interface Plan
    plan = InterfacePlanGenerator(api_key=api_key).generate(prd_doc)
    screens = plan.get("interfaces", [])
    results["stages"]["plan"] = {
        "screen_count": len(screens),
        "screen_ids": [s.get("id", "?") for s in screens],
    }
    print(f"[Plan] {len(screens)} screens: {[s.get('id','?') for s in screens]}")

    # Stage 2: Asset Analysis
    assets = AssetAnalyzer(api_key=api_key).analyze(prd_doc, plan)
    asset_count = len(assets.get("assets", []))
    results["stages"]["assets"] = {"count": asset_count}
    print(f"[Assets] {asset_count} assets")

    # Stage 3: Wireframe Generation
    ref_wf = golden_wf if with_golden else None
    wf_gen = WireframeGenerator(api_key=api_key)
    if golden_wf:
        wireframe, best_score = wf_gen.generate_best_of_n(
            prd_doc, plan, assets,
            golden_wireframe=golden_wf, n=3,
            reference_wireframe=ref_wf,
        )
        print(f"[Wireframe] Best-of-3 selected (score={best_score:.0%})")
    else:
        wireframe = wf_gen.generate(prd_doc, plan, assets, reference_wireframe=ref_wf)
    wf_screens = wireframe.get("interfaces", [])
    results["stages"]["wireframe"] = {
        "screen_count": len(wf_screens),
        "total_elements": sum(len(s.get("elements", [])) for s in wf_screens),
    }
    print(f"[Wireframe] {len(wf_screens)} screens, "
          f"{sum(len(s.get('elements',[])) for s in wf_screens)} elements")
    for s in wf_screens:
        print(f"  [{s.get('interface_id','?')}] {len(s.get('elements',[]))} elements, "
              f"nav→{s.get('children', [])}")

    # Evaluation
    print(f"\n--- Evaluation ---")

    # Self-metrics (always available)
    lc = _check_layout_completeness(wireframe)
    et = _check_element_types(wireframe)
    print(f"  layout_completeness: {lc.score:.0%} {'PASS' if lc.passed else 'FAIL'} — {lc.detail}")
    print(f"  element_types: {et.score:.0%} {'PASS' if et.passed else 'FAIL'} — {et.detail}")
    results["self_metrics"] = {
        "layout_completeness": lc.score,
        "element_types": et.score,
    }

    # Golden comparison (if available)
    if golden_wf:
        report = evaluate(wireframe, golden_wf)
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

        if with_semantic:
            sem = semantic_evaluate(wireframe, golden_wf, prd_doc, api_key)
            print(f"\n  Semantic: {sem.score:.0%} {'PASS' if sem.passed else 'FAIL'} — {sem.detail}")
            results["semantic"] = {"score": sem.score, "detail": sem.detail}
    else:
        print("\n  (No golden sample — self-metrics only)")

    elapsed = time.time() - t0
    results["elapsed_sec"] = round(elapsed, 1)
    print(f"\nDone in {elapsed:.1f}s")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="flappy", choices=list(GAMES.keys()) + ["all"])
    parser.add_argument("--with-golden", action="store_true")
    parser.add_argument("--semantic", action="store_true")
    args = parser.parse_args()

    if args.game == "all":
        all_results = {}
        for g in GAMES:
            r = run_pdca(
                game=g,
                with_golden=args.with_golden,
                with_semantic=args.semantic,
            )
            all_results[g] = r
        print("\n" + "=" * 60)
        print("CROSS-PRODUCT SUMMARY")
        print("=" * 60)
        for g, r in all_results.items():
            structural = r.get("structural", {}).get("overall", "N/A")
            if isinstance(structural, float):
                structural = f"{structural:.0%}"
            layout = r.get("self_metrics", {}).get("layout_completeness", 0)
            types_ = r.get("self_metrics", {}).get("element_types", 0)
            print(f"  {g:8s}: structural={structural:>5s}  "
                  f"layout={layout:.0%}  types={types_:.0%}  "
                  f"screens={r['stages']['wireframe']['screen_count']}  "
                  f"time={r['elapsed_sec']}s")
    else:
        run_pdca(
            game=args.game,
            with_golden=args.with_golden,
            with_semantic=args.semantic,
        )
