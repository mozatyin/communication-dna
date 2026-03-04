#!/usr/bin/env python3
"""Edge case test: Very short conversation (4 messages) → PRD quality."""
from __future__ import annotations
import os, sys, time
from dataclasses import dataclass, field
from intention_graph.prd_generator import PrdGenerator

@dataclass
class SimpleGame:
    facts: list[str] = field(default_factory=list)

# 4 messages only — a vague game idea
CONVERSATION = [
    {"role": "user", "content": "I want to make a puzzle game where you connect colored pipes"},
    {"role": "host", "content": "Interesting! How does the puzzle mechanic work?"},
    {"role": "user", "content": "You have a grid, each side has colored dots, you draw lines to connect matching colors without crossing lines"},
    {"role": "host", "content": "So it's about pathfinding without intersections. Any progression or levels?"},
]

FACTS = [
    "Genre: Puzzle",
    "Mechanic: Connect matching colored dots with lines",
    "Constraint: Lines cannot cross each other",
    "Grid-based gameplay",
]


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: Set ANTHROPIC_API_KEY"); sys.exit(1)

    game = SimpleGame(facts=FACTS)
    session_info = {"uid": "eval_short", "session_id": "short_test", "language": "en"}

    print("=" * 70)
    print("  Edge Case: Very Short Conversation (4 messages)")
    print("=" * 70)

    gen = PrdGenerator(api_key=api_key)
    start = time.time()
    result = gen.generate_sync(game=game, conversation_history=CONVERSATION, session_info=session_info)
    print(f"Generated in {time.time()-start:.1f}s\n")

    prd = result["prd_document"]
    print(prd[:3000] + "\n..." if len(prd) > 3000 else prd)

    checks = {
        "Has all 4 sections": all(f"## {i}." in prd for i in range(1, 5)),
        "[INFERRED] tags (should be many)": prd.count("[INFERRED]") >= 2,
        "PRD length > 3000 chars": len(prd) > 3000,
        "IG available": result["metadata"]["ig_available"],
        "Mentions grid": "grid" in prd.lower(),
        "Mentions colored/colors": "color" in prd.lower(),
        "Mentions crossing/intersect": "cross" in prd.lower() or "intersect" in prd.lower(),
    }

    print(f"\n{'='*70}")
    for name, ok in checks.items():
        print(f"  [{'✅' if ok else '❌'}] {name}")
    print(f"\n  [INFERRED] count: {prd.count('[INFERRED]')}")
    print(f"  PRD length: {len(prd)} chars")
    print(f"  Metadata: {result['metadata']}")


if __name__ == "__main__":
    main()
