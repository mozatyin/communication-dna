#!/usr/bin/env python3
"""PRD Generator Quality Evaluation — Iteration Framework.

Simulates a real user persona describing a Roblox Top 50 game (Blox Fruits)
from scratch, generates PRD, and evaluates quality.

Usage:
    ANTHROPIC_API_KEY=sk-or-... python eval_prd_iteration.py
"""

from __future__ import annotations

import os
import sys
import json
import time
from dataclasses import dataclass, field

from intention_graph.prd_generator import PrdGenerator


@dataclass
class SimpleGame:
    facts: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
# PERSONA: Lucas "Luki" Ferreira
# ═══════════════════════════════════════════════════════════════════════════════
#
# Age: 14, Male, Brazilian (São Paulo)
# Culture: Latin American gaming culture, huge One Piece fan
# Profession: Middle school student, aspiring game dev
# Language: English (2nd language) — enthusiastic, informal, uses "bro",
#           "like", "you know", sometimes grammatically loose
# Personality: Hyper-creative, competitive, jumps between ideas,
#              loves explaining combat details, gets excited easily
# Background: 3000+ hours on Roblox, plays competitively, watches anime daily
# Goal: Wants to build "the ultimate anime action RPG" on Roblox
#
# He is describing Blox Fruits from memory, as if it's his original idea.
# ═══════════════════════════════════════════════════════════════════════════════

CONVERSATION = [
    {
        "role": "user",
        "content": (
            "ok so I have this idea for a game right, its like an anime action RPG "
            "but on the ocean. players sail between islands fighting enemies and "
            "getting stronger. the main thing is you can eat special fruits that "
            "give you crazy superpowers like fire or ice or turning into a dragon"
        ),
    },
    {
        "role": "host",
        "content": (
            "That sounds awesome — an anime-inspired action RPG with island "
            "exploration and supernatural fruit powers! Can you tell me more "
            "about how the fruit system works?"
        ),
    },
    {
        "role": "user",
        "content": (
            "yeah so the fruits are the biggest thing. there are like 3 categories — "
            "Natural type which is like controlling elements (fire, ice, light, magma), "
            "Beast type where you literally transform into animals or mythical creatures "
            "like a dragon or phoenix, and then Paramecia type which gives you weird "
            "body powers like rubber or barrier or string. each fruit has 4-5 special "
            "moves you unlock by using it more. but heres the catch — you can only "
            "have ONE fruit at a time. if you eat a new one you lose the old one"
        ),
    },
    {
        "role": "host",
        "content": (
            "So it's a meaningful choice — players commit to one fruit and master it. "
            "The three categories with different playstyles is great variety. "
            "How does the rest of the combat work beyond fruit abilities?"
        ),
    },
    {
        "role": "user",
        "content": (
            "combat is actually really deep bro. you have 4 ways to fight — "
            "melee/martial arts with combos, swords with special slash moves, "
            "guns for ranged damage, and your fruit powers. each weapon style "
            "has its own mastery bar that levels up the more you use it, and "
            "you unlock better moves as mastery goes up. plus theres fighting "
            "styles you can learn from NPCs like Dark Step or Superhuman that "
            "give you different combo strings"
        ),
    },
    {
        "role": "host",
        "content": (
            "Four combat pillars with independent mastery progression — that's "
            "a lot of build variety. How does the player progress through the world?"
        ),
    },
    {
        "role": "user",
        "content": (
            "so the world is split into 3 seas. First Sea is like level 1 to 700, "
            "its where beginners start. theres like 13 islands each with different "
            "level ranges. you go to an island, find the quest giver NPC, they tell "
            "you to kill X enemies, you do it, get XP and money, level up, then sail "
            "to the next island. Second Sea is level 700-1500 and its way harder with "
            "better fruits and tougher bosses. Third Sea is endgame 1500-2550 with "
            "the craziest stuff"
        ),
    },
    {
        "role": "host",
        "content": (
            "A three-tier world progression with escalating difficulty. "
            "What about character stats and builds?"
        ),
    },
    {
        "role": "user",
        "content": (
            "every level you get stat points to put into 5 stats — Melee for "
            "punch damage, Defense for HP, Sword for sword damage, Gun for gun "
            "damage, and Blox Fruit for fruit ability damage and energy. you gotta "
            "choose your build early because you cant put points in everything. "
            "like a fruit user would max Blox Fruit and Defense, a swordsman would "
            "max Sword and Defense. but you CAN reset your stats with in-game currency"
        ),
    },
    {
        "role": "host",
        "content": (
            "Smart stat system that forces specialization but allows respec. "
            "Tell me about the PvP side of things."
        ),
    },
    {
        "role": "user",
        "content": (
            "PvP is huge!! theres a bounty system — when you kill other players "
            "you get bounty points and they can see your bounty. high bounty players "
            "are like wanted targets everyone tries to hunt. theres also a faction "
            "system where you pick Pirates or Marines at the start, and the two sides "
            "fight each other. oh and when you die in PvP you get temporary "
            "invincibility so people cant spawn camp you"
        ),
    },
    {
        "role": "host",
        "content": (
            "Bounty hunting adds a great emergent PvP layer. What about "
            "cooperative content?"
        ),
    },
    {
        "role": "user",
        "content": (
            "raids bro! theres boss raids where you need a team to take down "
            "really strong bosses that spawn on timers. beating raid bosses gives "
            "you special items and sometimes rare fruits. theres also a thing called "
            "Awakening where you can upgrade your fruit to a stronger version with "
            "new moves, but you need to complete specific raid challenges to unlock "
            "each awakened move. its like the endgame grind"
        ),
    },
    {
        "role": "host",
        "content": (
            "Raids for co-op plus Awakening as endgame progression tied to raid "
            "completion — clever design. Any social/economy features?"
        ),
    },
    {
        "role": "user",
        "content": (
            "yeah trading is massive! players trade fruits with each other, "
            "and rare fruits are worth a ton. theres like a whole economy around "
            "fruit values. you can also buy stuff from NPC shops with Beli (the "
            "in-game money) or with Fragments you get from raids. theres also "
            "a race system — your character has a race (Human, Shark, Angel, etc) "
            "and you can awaken your race to get special passive buffs like faster "
            "swimming or flight"
        ),
    },
    {
        "role": "host",
        "content": (
            "So there's a player-driven fruit economy plus a race system with "
            "awakening. What about the visual and audio style?"
        ),
    },
    {
        "role": "user",
        "content": (
            "its Roblox style so blocky characters but with anime effects — like "
            "when you use a fruit power theres big flashy particle effects, screen "
            "shake on big hits, the camera zooms for ultimate moves. the islands "
            "all look different — snow island, desert island, jungle, underwater "
            "city. music changes per island too, like epic battle music for boss "
            "areas and chill exploration music for safe zones. sound effects are "
            "really punchy for combat — slashes, explosions, impact sounds"
        ),
    },
]

FACTS = [
    "Genre: Anime-inspired action RPG / MMORPG",
    "Setting: Ocean world with island archipelago",
    "Platform: Roblox",
    "Core mechanic: Supernatural fruit powers (one fruit per player)",
    "Fruit categories: Natural (elemental), Beast (transformation), Paramecia (body alteration)",
    "Each fruit has 4-5 unlockable special moves",
    "Combat: 4 pillars — Melee, Sword, Gun, Fruit abilities",
    "Each combat style has independent mastery progression",
    "Fighting styles learned from NPCs (Dark Step, Superhuman, etc.)",
    "World: 3 seas — First (1-700), Second (700-1500), Third (1500-2550)",
    "13+ islands with level-gated quest progression",
    "Quests: Kill X enemies from NPC quest givers",
    "5 stats: Melee, Defense, Sword, Gun, Blox Fruit — stat points per level",
    "Stat reset available with in-game currency",
    "PvP: Bounty system — kill players to earn bounty, become hunted target",
    "Factions: Pirates vs Marines",
    "PvP death: Temporary invincibility anti-spawn-camp",
    "Raids: Timed boss spawns requiring team coordination",
    "Awakening: Upgrade fruit moves via raid challenges (endgame)",
    "Trading: Player-to-player fruit trading economy",
    "Currency: Beli (quests) + Fragments (raids)",
    "Race system: Human, Shark, Angel, etc. — awakened races give passive buffs",
    "Visual: Roblox blocky + anime particle effects, screen shake, camera zoom",
    "Islands: Themed biomes (snow, desert, jungle, underwater)",
    "Audio: Per-island music, punchy combat SFX",
]


# ═══════════════════════════════════════════════════════════════════════════════
# Quality Evaluation Criteria
# ═══════════════════════════════════════════════════════════════════════════════

EXPECTED_SYSTEMS = [
    ("Fruit/Devil Fruit Power System", [
        "three categories (Natural/Beast/Paramecia)",
        "one fruit limit",
        "4-5 moves per fruit",
        "mastery/unlock progression",
    ]),
    ("Combat System", [
        "four pillars (melee/sword/gun/fruit)",
        "mastery per weapon type",
        "fighting styles from NPCs",
        "combo mechanics",
    ]),
    ("World/Island Progression", [
        "three seas with level gates",
        "island-to-island quest chain",
        "quest structure (kill X enemies)",
        "sailing between islands",
    ]),
    ("Stat/Build System", [
        "5 stat categories",
        "points per level",
        "build specialization",
        "stat reset option",
    ]),
    ("PvP & Bounty System", [
        "bounty from killing players",
        "wanted target mechanic",
        "Pirates vs Marines factions",
        "anti-spawn-camp invincibility",
    ]),
    ("Raid & Boss System", [
        "timed boss spawns",
        "team coordination or cooperation",
        "special rewards (items/fruits)",
    ]),
    ("Awakening System", [
        "fruit upgrade to stronger version",
        "new/enhanced moves",
        "tied to raid challenges",
        "endgame progression",
    ]),
    ("Economy & Trading", [
        "player-to-player fruit trading",
        "Beli currency from quests",
        "Fragments from raids",
        "NPC shops",
    ]),
    ("Race System", [
        "multiple races (Human/Shark/Angel)",
        "race awakening",
        "passive buffs",
    ]),
]


def evaluate_prd(prd_text: str) -> dict:
    """Evaluate PRD quality against expected content."""
    results = {
        "structure": {},
        "systems": {},
        "detail_scores": {},
        "issues": [],
    }

    # 1. Structure check
    for section_num, section_name in [
        ("1", "游戏总览"),
        ("2", "核心游戏循环"),
        ("3", "游戏系统"),
        ("4", "美术与音效风格"),
    ]:
        found = f"## {section_num}." in prd_text
        results["structure"][section_name] = found
        if not found:
            results["issues"].append(f"Missing section: ## {section_num}. {section_name}")

    # 2. System coverage
    prd_lower = prd_text.lower()
    for system_name, expected_details in EXPECTED_SYSTEMS:
        found_details = []
        missing_details = []
        for detail in expected_details:
            # Check for key terms from detail description
            # Split on spaces and common separators, stem-like matching
            raw_words = detail.lower().replace("/", " ").replace("-", " ").split()
            keywords = [w.strip("()") for w in raw_words if len(w) > 3]
            # Also check word stems (first 4+ chars)
            stems = [kw[:min(len(kw), 6)] for kw in keywords if len(kw) >= 4]
            if any(kw in prd_lower for kw in keywords) or any(s in prd_lower for s in stems):
                found_details.append(detail)
            else:
                missing_details.append(detail)

        coverage = len(found_details) / len(expected_details) if expected_details else 0
        results["systems"][system_name] = {
            "coverage": coverage,
            "found": found_details,
            "missing": missing_details,
        }
        if coverage < 0.5:
            results["issues"].append(
                f"Low coverage for {system_name}: {coverage:.0%} — "
                f"missing: {', '.join(missing_details)}"
            )

    # 3. Detail quality indicators
    results["detail_scores"]["total_length"] = len(prd_text)
    results["detail_scores"]["num_subsections"] = prd_text.count("###")
    results["detail_scores"]["has_inferred_tags"] = "[INFERRED]" in prd_text
    results["detail_scores"]["num_bold_terms"] = prd_text.count("**")

    # 4. Overall score
    structure_score = sum(results["structure"].values()) / 4
    system_scores = [s["coverage"] for s in results["systems"].values()]
    avg_system_coverage = sum(system_scores) / len(system_scores) if system_scores else 0
    length_score = min(1.0, len(prd_text) / 5000)  # expect at least 5000 chars

    results["overall_score"] = (
        structure_score * 0.2
        + avg_system_coverage * 0.6
        + length_score * 0.2
    )

    return results


def print_evaluation(eval_result: dict, version: str = "v1"):
    """Pretty-print evaluation results."""
    print(f"\n{'='*70}")
    print(f"  PRD Quality Evaluation — {version}")
    print(f"{'='*70}")

    print("\n📐 Structure:")
    for section, found in eval_result["structure"].items():
        print(f"  [{'✅' if found else '❌'}] {section}")

    print("\n🎮 System Coverage:")
    for system, data in eval_result["systems"].items():
        bar = "█" * int(data["coverage"] * 10) + "░" * (10 - int(data["coverage"] * 10))
        print(f"  {bar} {data['coverage']:.0%}  {system}")
        if data["missing"]:
            for m in data["missing"]:
                print(f"            ⚠️  missing: {m}")

    print(f"\n📊 Detail Metrics:")
    d = eval_result["detail_scores"]
    print(f"  PRD length: {d['total_length']} chars")
    print(f"  Subsections (###): {d['num_subsections']}")
    print(f"  [INFERRED] tags: {'yes' if d['has_inferred_tags'] else 'no'}")

    print(f"\n🏆 Overall Score: {eval_result['overall_score']:.1%}")

    if eval_result["issues"]:
        print(f"\n⚠️  Issues ({len(eval_result['issues'])}):")
        for issue in eval_result["issues"]:
            print(f"  - {issue}")
    else:
        print("\n✅ No issues found!")


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    game = SimpleGame(facts=FACTS)
    session_info = {
        "uid": "eval_lucas",
        "session_id": "blox_fruits_eval",
        "language": "en",
    }

    print("=" * 70)
    print("  PRD Generator Evaluation")
    print("  Game: Blox Fruits (Roblox #2, 52.9B visits)")
    print("  Persona: Lucas 'Luki' Ferreira, 14yo Brazilian, anime fan")
    print("  Language: English (informal)")
    print("=" * 70)

    generator = PrdGenerator(api_key=api_key)

    print("\nGenerating PRD...")
    start = time.time()
    result = generator.generate_sync(
        game=game,
        conversation_history=CONVERSATION,
        session_info=session_info,
    )
    elapsed = time.time() - start
    print(f"Done in {elapsed:.1f}s")

    # Print full PRD
    print("\n" + "=" * 70)
    print("📄 GENERATED PRD:")
    print("=" * 70)
    print(result["prd_document"])
    print("=" * 70)

    # Print summary
    print(f"\n📋 Summary: {result['prd_summary']}")

    # Print metadata
    print(f"\n📊 Metadata:")
    for k, v in result["metadata"].items():
        print(f"  {k}: {v}")

    # Evaluate
    eval_result = evaluate_prd(result["prd_document"])
    print_evaluation(eval_result, "v1.0")

    # Save results
    output = {
        "persona": {
            "name": "Lucas 'Luki' Ferreira",
            "age": 14,
            "gender": "male",
            "culture": "Brazilian",
            "profession": "middle school student",
            "language": "English (informal, 2nd language)",
            "personality": "hyper-creative, competitive, anime fan",
            "goal": "build the ultimate anime action RPG",
        },
        "game": "Blox Fruits (Roblox Top 2)",
        "conversation_messages": len(CONVERSATION),
        "facts_count": len(FACTS),
        "prd_document": result["prd_document"],
        "prd_summary": result["prd_summary"],
        "metadata": result["metadata"],
        "evaluation": {
            "structure": eval_result["structure"],
            "system_coverage": {
                k: v["coverage"] for k, v in eval_result["systems"].items()
            },
            "overall_score": eval_result["overall_score"],
            "issues": eval_result["issues"],
        },
        "generation_time_seconds": elapsed,
    }

    with open("eval_prd_v1_results.json", "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to eval_prd_v1_results.json")


if __name__ == "__main__":
    main()
