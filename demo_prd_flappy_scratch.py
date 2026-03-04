#!/usr/bin/env python3
"""Demo: A simulated user describes a Flappy Bird-like game from scratch.

The user has never heard of "Flappy Bird" — they describe the concept
purely through game design conversation. We test whether the PRD output
is detailed enough to build the game from.

Usage:
    ANTHROPIC_API_KEY=sk-or-... python demo_prd_flappy_scratch.py
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

from intention_graph.prd_generator import PrdGenerator


@dataclass
class SimpleGame:
    facts: list[str] = field(default_factory=list)


# ── Simulated Conversation: User describes "Flappy Bird" from scratch ────────

CONVERSATION = [
    {
        "role": "user",
        "content": "我想做一个很简单的手机小游戏，就是一只小鸟在飞，玩家要控制它不要撞到东西",
    },
    {
        "role": "host",
        "content": "听起来是个不错的休闲游戏概念！能具体说说小鸟怎么飞吗？是自动往前飞还是玩家控制方向？",
    },
    {
        "role": "user",
        "content": "小鸟是自动往右边飞的，一直往前，不会停。玩家唯一能做的就是点屏幕，每点一下小鸟就往上跳一下。如果不点的话，小鸟会因为重力一直往下掉",
    },
    {
        "role": "host",
        "content": "所以核心操作就是单点触控，对抗重力。那障碍物是什么样的？",
    },
    {
        "role": "user",
        "content": "障碍物是一对一对的管子，上面一根从天花板往下伸，下面一根从地面往上伸，中间留一个缺口让小鸟飞过去。管子之间的缺口大小是固定的，但是缺口的上下位置是随机的，有时候偏上有时候偏下",
    },
    {
        "role": "host",
        "content": "经典的通道式障碍设计！管子之间的间距怎么安排？难度会变化吗？",
    },
    {
        "role": "user",
        "content": "每隔一段固定的水平距离就出现一对管子。一开始缺口大一点，让玩家上手。后面可以考虑缺口慢慢变小，或者管子之间的水平间距缩短，但一开始先做固定难度就好",
    },
    {
        "role": "host",
        "content": "明白了，先实现固定难度的基础版。碰撞了会怎样？",
    },
    {
        "role": "user",
        "content": "小鸟碰到管子或者碰到地面就死了，游戏立刻结束，显示分数。碰到天花板也算死。死了之后可以点重新开始。分数就是成功飞过的管子对数，每飞过一对加一分",
    },
    {
        "role": "host",
        "content": "一碰就死，记管子数为分数，很清晰。有没有最高分记录？",
    },
    {
        "role": "user",
        "content": "对，要记录历史最高分，显示在游戏结束画面上。如果打破最高分要有一个明显的提示，比如一个NEW的标志",
    },
    {
        "role": "host",
        "content": "好的。画面风格有什么想法吗？",
    },
    {
        "role": "user",
        "content": "要很可爱的像素风格，小鸟圆圆的有翅膀会扇动。背景是蓝天白云和绿色的地面，管子是绿色的。整体颜色要鲜艳，看起来开心。白天的场景就好",
    },
    {
        "role": "host",
        "content": "像素风可爱小鸟加明亮配色，很讨喜。小鸟飞的时候有什么动画效果吗？",
    },
    {
        "role": "user",
        "content": "小鸟往上飞的时候身体微微上仰，往下掉的时候慢慢下倾，有一种真实飞翔的感觉。翅膀要不停扇动，点击的时候扇动更快。死的时候小鸟要翻转着掉下去",
    },
    {
        "role": "host",
        "content": "这些动画细节能让操作感变好很多。音效方面呢？",
    },
    {
        "role": "user",
        "content": "点击的时候有一个轻轻的「噗」的翅膀声，飞过管子的时候有一个清脆的「叮」的得分声，撞到东西的时候有一个「啪」的碰撞声，然后掉到地上有一个「咚」。整体音效要可爱不要吓人",
    },
    {
        "role": "host",
        "content": "四种核心音效，都是可爱风格。游戏开始前有什么界面吗？",
    },
    {
        "role": "user",
        "content": "开始界面就显示游戏名字，小鸟在中间上下浮动，下面写点击开始。点了之后有个321倒计时或者直接开始都行。结束画面显示当前分数、最高分，还有一个重新开始按钮",
    },
]

FACTS = [
    "游戏类型: 横向卷轴躲避游戏",
    "平台: 手机",
    "操作: 单点触控，点击=小鸟上跳",
    "角色: 像素小鸟，受重力影响",
    "小鸟自动向右匀速飞行",
    "障碍: 上下成对管子，中间留缺口",
    "缺口位置随机，大小固定（初版）",
    "管子等距出现",
    "碰撞=即死（管子、地面、天花板）",
    "计分: 每飞过一对管子+1分",
    "记录历史最高分，破纪录显示NEW标志",
    "画面: 像素风，蓝天白云绿地，鲜艳配色",
    "管子为绿色",
    "小鸟动画: 扇翅、上仰/下倾、死亡翻转",
    "音效: 扇翅声、得分叮声、碰撞声、落地声",
    "界面: 开始画面(小鸟浮动) + 结束画面(分数+最高分+重玩)",
]


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    game = SimpleGame(facts=FACTS)
    session_info = {
        "uid": "demo_user",
        "session_id": "flappy_scratch_demo",
        "language": "zh",
    }

    print("=" * 70)
    print("  PRD Generator Demo: 从零描述的「小鸟飞行」游戏")
    print("  (模拟用户不知道 Flappy Bird，纯靠描述)")
    print("=" * 70)
    print()

    generator = PrdGenerator(api_key=api_key)
    result = generator.generate_sync(
        game=game,
        conversation_history=CONVERSATION,
        session_info=session_info,
    )

    print("📄 PRD Document:")
    print("-" * 70)
    print(result["prd_document"])
    print("-" * 70)
    print()
    print("📋 Summary:")
    print(result["prd_summary"])
    print()
    print("📊 Metadata:")
    for key, value in result["metadata"].items():
        print(f"  {key}: {value}")
    print()

    # Quick validation
    prd = result["prd_document"]
    checks = {
        "Section 1 (游戏总览)": "## 1." in prd,
        "Section 2 (核心游戏循环)": "## 2." in prd,
        "Section 3 (游戏系统)": "## 3." in prd,
        "Section 4 (美术与音效)": "## 4." in prd,
        "[INFERRED] tags present": "[INFERRED]" in prd,
        "IG available": result["metadata"]["ig_available"],
        "Core intention populated": bool(result["metadata"]["core_intention"]),
        "Intentions extracted": result["metadata"]["num_intentions"] > 0,
    }

    print("✅ Validation:")
    all_pass = True
    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print(f"  [{status}] {check}")

    if all_pass:
        print("\n  All checks passed!")
    else:
        print("\n  Some checks failed — review output above.")


if __name__ == "__main__":
    main()
