#!/usr/bin/env python3
"""Demo: Generate a full PRD from a single sentence.

Usage:
    ANTHROPIC_API_KEY=sk-or-... python demo_one_sentence_prd.py [flappy|kings]

Examples:
    python demo_one_sentence_prd.py flappy   # "做一个Flappy Bird"
    python demo_one_sentence_prd.py kings    # "王者荣耀"
"""

from __future__ import annotations

import os
import sys

from intention_graph.one_sentence_prd import OneSentencePrd

EXAMPLES = {
    "flappy": "做一个Flappy Bird",
    "kings": "王者荣耀",
}


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    example_name = sys.argv[1] if len(sys.argv) > 1 else "flappy"
    if example_name not in EXAMPLES:
        print(f"Unknown example: {example_name}")
        print(f"Available: {', '.join(EXAMPLES.keys())}")
        sys.exit(1)

    sentence = EXAMPLES[example_name]
    print(f"Input: \"{sentence}\"")
    print("=" * 60)

    generator = OneSentencePrd(api_key=api_key)
    result = generator.generate(sentence)

    print("\nPRD Document:\n")
    print(result["prd_document"])
    print("\n" + "=" * 60)
    print("\nSummary:\n")
    print(result["prd_summary"])
    print("\n" + "=" * 60)
    print("\nMetadata:\n")
    for key, value in result["metadata"].items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
