#!/usr/bin/env python3
"""Demo: Generate a full PRD from a single sentence.

Usage:
    ANTHROPIC_API_KEY=sk-or-... python demo_one_sentence_prd.py [flappy|kings|1943|pvz|hollow]
    ANTHROPIC_API_KEY=sk-or-... python demo_one_sentence_prd.py --interactive flappy

Examples:
    python demo_one_sentence_prd.py flappy        # Auto mode: "做一个Flappy Bird"
    python demo_one_sentence_prd.py kings          # Auto mode: "王者荣耀"
    python demo_one_sentence_prd.py --interactive  # Interactive: asks you design questions
"""

from __future__ import annotations

import os
import sys

from intention_graph.one_sentence_prd import OneSentencePrd

EXAMPLES = {
    "flappy": "做一个Flappy Bird",
    "kings": "王者荣耀",
    "1943": "请帮我生成一个1943模拟游戏",
    "pvz": "做一个植物大战僵尸",
    "hollow": "做一个空洞骑士",
}


def interactive_answer(questions: list[dict[str, str]]) -> list[str]:
    """Prompt user to answer design questions interactively."""
    print("\n" + "=" * 60)
    print("Design questions detected! Please answer:")
    print("=" * 60)

    answers = []
    for i, q in enumerate(questions):
        print(f"\n  Q{i+1}: {q['question']}")
        answer = input(f"  A{i+1}: ").strip()
        if not answer:
            answer = "(no preference)"
        answers.append(answer)

    print("=" * 60 + "\n")
    return answers


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    # Parse args
    args = sys.argv[1:]
    interactive = "--interactive" in args
    args = [a for a in args if a != "--interactive"]

    example_name = args[0] if args else "flappy"
    if example_name not in EXAMPLES:
        print(f"Unknown example: {example_name}")
        print(f"Available: {', '.join(EXAMPLES.keys())}")
        sys.exit(1)

    sentence = EXAMPLES[example_name]
    mode = "interactive" if interactive else "auto"
    print(f"Input: \"{sentence}\"")
    print(f"Mode: {mode}")
    print("=" * 60)

    generator = OneSentencePrd(api_key=api_key)

    answer_fn = interactive_answer if interactive else None
    result = generator.generate(sentence, answer_fn=answer_fn)

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
