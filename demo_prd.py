#!/usr/bin/env python3
"""Demo: PRD generation from sample game design conversations.

Usage:
    ANTHROPIC_API_KEY=sk-or-... python demo_prd.py [tower_defense|flappy]
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

from intention_graph.prd_generator import PrdGenerator


@dataclass
class SimpleGame:
    """Minimal game object with facts list."""
    facts: list[str] = field(default_factory=list)


# ── Sample Conversations ─────────────────────────────────────────────────────

TOWER_DEFENSE_CONVERSATION = [
    {"role": "user", "content": "我想做一个塔防游戏，中世纪奇幻风格的"},
    {"role": "host", "content": "听起来很有趣！你想要什么样的防御塔类型？"},
    {"role": "user", "content": "有弓箭塔、魔法塔、炮塔三种，弓箭塔打轻甲快，魔法塔范围伤害，炮塔打重甲"},
    {"role": "host", "content": "这三种塔在面对不同怪物时各有优势，很好的设计！怪物方面你有什么想法？"},
    {"role": "user", "content": "怪物有克制关系，轻甲怪速度快但血少，护盾怪扛物理伤害，重甲怪慢但血厚"},
    {"role": "host", "content": "这个克制系统让玩家需要搭配不同塔来应对不同怪物，增加了策略深度。关卡设计呢？"},
    {"role": "user", "content": "每关10波怪物，越到后面越难，最后一波是Boss。Boss有特殊技能，比如召唤小怪或者加速"},
    {"role": "host", "content": "Boss机制很棒！玩家在通关之间有什么进度系统吗？"},
    {"role": "user", "content": "通关可以获得金币升级塔的属性，比如攻击力、射程、攻速。还有解锁新塔的科技树"},
    {"role": "host", "content": "科技树和升级系统为游戏增加了长线目标。你对美术风格有什么具体想法吗？"},
    {"role": "user", "content": "像素风格的，Q版可爱一点，颜色鲜艳。音乐要有中世纪感觉但不要太严肃"},
]

TOWER_DEFENSE_FACTS = [
    "游戏类型: 塔防",
    "画面风格: 中世纪奇幻 像素风 Q版",
    "防御塔: 弓箭塔(打轻甲)、魔法塔(范围伤害)、炮塔(打重甲)",
    "怪物: 轻甲(快速)、护盾(抗物理)、重甲(慢但血厚)",
    "关卡: 每关10波怪物，最后一波Boss",
    "Boss: 有特殊技能(召唤小怪/加速)",
    "进度系统: 金币升级塔属性 + 科技树解锁新塔",
    "音乐: 中世纪风格 轻松基调",
]

FLAPPY_CONVERSATION = [
    {"role": "user", "content": "I want to make a flappy bird clone but in space"},
    {"role": "host", "content": "A space-themed flappy bird sounds fun! What kind of character would the player control?"},
    {"role": "user", "content": "A little astronaut with a jetpack. Each tap gives a burst of thrust upward"},
    {"role": "host", "content": "Nice! What would the obstacles be in a space setting?"},
    {"role": "user", "content": "Asteroid fields with gaps to fly through. Some asteroids rotate. And there are space debris that moves horizontally"},
    {"role": "host", "content": "Dynamic obstacles! Any power-ups or special mechanics?"},
    {"role": "user", "content": "Yeah, you can collect oxygen tanks to get a shield that lets you survive one hit. And there are speed boost rings that give you points multiplier"},
    {"role": "host", "content": "The shield and multiplier add nice risk-reward choices. What about progression?"},
    {"role": "user", "content": "High score leaderboard, and you unlock cosmetic skins for the astronaut as you hit score milestones"},
    {"role": "host", "content": "Great! Any visual style preferences?"},
    {"role": "user", "content": "Clean vector art, dark space background with colorful nebulas. Neon accents on the UI"},
]

FLAPPY_FACTS = [
    "Game type: Flappy Bird clone",
    "Setting: Space",
    "Character: Astronaut with jetpack",
    "Control: Tap for thrust burst",
    "Obstacles: Asteroid fields (gaps), rotating asteroids, moving space debris",
    "Power-ups: Oxygen tank (shield), speed boost rings (score multiplier)",
    "Progression: High score leaderboard + cosmetic skin unlocks",
    "Art style: Vector art, dark space, colorful nebulas, neon UI",
]

SCENARIOS = {
    "tower_defense": {
        "conversation": TOWER_DEFENSE_CONVERSATION,
        "facts": TOWER_DEFENSE_FACTS,
        "language": "zh",
    },
    "flappy": {
        "conversation": FLAPPY_CONVERSATION,
        "facts": FLAPPY_FACTS,
        "language": "en",
    },
}


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    scenario_name = sys.argv[1] if len(sys.argv) > 1 else "tower_defense"
    if scenario_name not in SCENARIOS:
        print(f"Unknown scenario: {scenario_name}")
        print(f"Available: {', '.join(SCENARIOS.keys())}")
        sys.exit(1)

    scenario = SCENARIOS[scenario_name]
    game = SimpleGame(facts=scenario["facts"])
    session_info = {
        "uid": "demo_user",
        "session_id": "demo_session",
        "language": scenario["language"],
    }

    print(f"Generating PRD for scenario: {scenario_name}")
    print(f"Language: {scenario['language']}")
    print("=" * 60)

    generator = PrdGenerator(api_key=api_key)
    result = generator.generate_sync(
        game=game,
        conversation_history=scenario["conversation"],
        session_info=session_info,
    )

    print("\n📄 PRD Document:\n")
    print(result["prd_document"])
    print("\n" + "=" * 60)
    print("\n📋 Summary:\n")
    print(result["prd_summary"])
    print("\n" + "=" * 60)
    print("\n📊 Metadata:\n")
    for key, value in result["metadata"].items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
