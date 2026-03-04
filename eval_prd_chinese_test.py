#!/usr/bin/env python3
"""Test PRD generation with the Chinese tower defense conversation.

Verifies cross-language quality: Chinese input → Chinese PRD.
"""
from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field

from intention_graph.prd_generator import PrdGenerator


@dataclass
class SimpleGame:
    facts: list[str] = field(default_factory=list)


# Reuse the tower defense conversation from demo_prd_flappy_scratch
CONVERSATION = [
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

FACTS = [
    "游戏类型: 塔防",
    "画面风格: 中世纪奇幻 像素风 Q版",
    "防御塔: 弓箭塔(打轻甲)、魔法塔(范围伤害)、炮塔(打重甲)",
    "怪物: 轻甲(快速)、护盾(抗物理)、重甲(慢但血厚)",
    "克制系统: 弓箭塔→轻甲、魔法塔→护盾、炮塔→重甲",
    "关卡: 每关10波怪物，最后一波Boss",
    "Boss: 有特殊技能(召唤小怪/加速)",
    "进度: 金币升级塔属性(攻击力/射程/攻速)",
    "科技树: 解锁新塔",
    "美术: 像素风 Q版 鲜艳颜色",
    "音乐: 中世纪风格 轻松基调",
]

# Expected Chinese content checks
CHINESE_CHECKS = [
    ("Section headers", lambda p: "## 1." in p and "## 2." in p and "## 3." in p and "## 4." in p),
    ("Written in Chinese", lambda p: sum(1 for c in p if '\u4e00' <= c <= '\u9fff') > 200),
    ("弓箭塔 mentioned", lambda p: "弓箭塔" in p),
    ("魔法塔 mentioned", lambda p: "魔法塔" in p),
    ("炮塔 mentioned", lambda p: "炮塔" in p),
    ("克制 system", lambda p: "克制" in p or "轻甲" in p),
    ("10波 mentioned", lambda p: "10" in p and "波" in p),
    ("Boss mechanic", lambda p: "Boss" in p or "boss" in p or "BOSS" in p),
    ("科技树", lambda p: "科技树" in p),
    ("像素 style", lambda p: "像素" in p),
    ("[INFERRED] present", lambda p: "[INFERRED]" in p),
    ("如何运作 in systems", lambda p: "如何运作" in p),
    ("为何感觉良好 in systems", lambda p: "为何感觉良好" in p),
    ("设计考量 has questions", lambda p: "?" in p or "？" in p),
]


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    game = SimpleGame(facts=FACTS)
    session_info = {"uid": "eval_zh", "session_id": "tower_defense_zh", "language": "zh"}

    print("=" * 70)
    print("  Cross-Language Test: Chinese Tower Defense → Chinese PRD")
    print("=" * 70)

    generator = PrdGenerator(api_key=api_key)
    start = time.time()
    result = generator.generate_sync(game=game, conversation_history=CONVERSATION, session_info=session_info)
    elapsed = time.time() - start
    print(f"Generated in {elapsed:.1f}s\n")

    prd = result["prd_document"]
    print(prd)
    print("\n" + "=" * 70)
    print(f"Summary: {result['prd_summary']}")
    print(f"Metadata: {result['metadata']}")

    print(f"\n{'='*70}")
    print("  Chinese Quality Checks")
    print(f"{'='*70}")
    passed = 0
    for name, check in CHINESE_CHECKS:
        ok = check(prd)
        if ok:
            passed += 1
        print(f"  [{'✅' if ok else '❌'}] {name}")
    print(f"\nScore: {passed}/{len(CHINESE_CHECKS)} = {passed/len(CHINESE_CHECKS):.0%}")


if __name__ == "__main__":
    main()
