"""One-Sentence PRD: Generate a full PRD from a single sentence like "做一个Flappy Bird".

Orchestrates the existing IG pipeline (Connect → Expand → Clarify) with
web research and self-answering to produce comprehensive PRDs without
multi-turn conversation.

v2 — Key improvements over v1:
- Complexity detection: arcade games stay simple, no system inflation
- Faithful research: respects original game's design philosophy
- Genre-aware self-answer: focuses on real design tradeoffs, not generic questions
- Honest conversation synthesis: separates user-stated vs research-inferred
- System count limits based on complexity level
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import anthropic

from intention_graph.connect import Connect
from intention_graph.expand import Expand
from intention_graph.clarify import Clarify
from intention_graph.models import IntentionGraph, Transition
from intention_graph.prd_generator import (
    PrdGenerator,
    _PRD_SYSTEM_PROMPT,
    _graph_to_context,
    _parse_prd_response,
)
from intention_graph.web_search import research_game


# ── Complexity profiles ─────────────────────────────────────────────────────

_COMPLEXITY_PROFILES = {
    "arcade": {
        "max_systems": 4,
        "skip_expand": True,
        "research_chars": 1500,
        "conversation_turns": "6-8",
        "min_prd_chars": 3000,
        "prd_max_tokens": 6000,
        "research_constraint": (
            "This is a classic arcade game. Respect its simplicity.\n"
            "DO NOT add modern systems that the original game never had:\n"
            "- NO skill trees, talent systems, or character progression\n"
            "- NO equipment/gear systems or crafting\n"
            "- NO base building or management\n"
            "- NO gacha, battle passes, or live-service mechanics\n"
            "Focus ONLY on: core loop, controls, scoring, difficulty curve, "
            "and the specific mechanics that made this game iconic."
        ),
    },
    "casual": {
        "max_systems": 6,
        "skip_expand": False,
        "research_chars": 2000,
        "conversation_turns": "8-10",
        "min_prd_chars": 4500,
        "prd_max_tokens": 8000,
        "research_constraint": (
            "This is a casual game. Keep systems lightweight.\n"
            "Only include progression systems that are simple and natural.\n"
            "Avoid over-engineering with complex meta-game loops."
        ),
    },
    "mid-core": {
        "max_systems": 8,
        "skip_expand": False,
        "research_chars": 3000,
        "conversation_turns": "10-12",
        "min_prd_chars": 5500,
        "prd_max_tokens": 10000,
        "research_constraint": (
            "This is a mid-core game with moderate system depth.\n"
            "Include progression, economy, and social systems where appropriate.\n"
            "Balance depth with accessibility."
        ),
    },
    "hardcore": {
        "max_systems": 10,
        "skip_expand": False,
        "research_chars": 4000,
        "conversation_turns": "12-14",
        "min_prd_chars": 5000,
        "prd_max_tokens": 12000,
        "research_constraint": (
            "This is a complex, hardcore game with deep systems.\n"
            "Include comprehensive progression, economy, social, and meta-game systems.\n"
            "Detail is welcome — this audience expects depth."
        ),
    },
}


@dataclass
class GameInfo:
    """Structured game identification result."""
    game_name: str
    game_name_original: str
    language: str
    complexity: str  # arcade | casual | mid-core | hardcore
    genre: str
    era: str
    core_systems: list[str] = field(default_factory=list)


@dataclass
class SimpleGame:
    """Minimal game object for PrdGenerator compatibility."""
    facts: list[str] = field(default_factory=list)


class OneSentencePrd:
    """Generate a full PRD from a single sentence.

    v2 Pipeline:
    1. Identify game (name, complexity, genre, era, core systems)
    2. Research with faithfulness constraints
    3. Connect → Expand(conditional) → Clarify (existing IG pipeline)
    4. Self-answer ambiguities with genre context
    5. Synthesize honest conversation (user-stated vs inferred)
    6. PrdGenerator (existing, unchanged)
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        kwargs: dict = {"api_key": api_key}
        if api_key.startswith("sk-or-"):
            kwargs["base_url"] = "https://openrouter.ai/api"
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model
        self._connect = Connect(api_key=api_key, model=model)
        self._expand = Expand(api_key=api_key, model=model)
        self._clarify = Clarify(api_key=api_key, model=model)
        self._prd_generator = PrdGenerator(api_key=api_key, model=model)

    def generate(
        self,
        sentence: str,
        answer_fn: Callable[[list[dict[str, str]]], list[str]] | None = None,
    ) -> dict[str, Any]:
        """Full pipeline: sentence → PRD.

        Args:
            sentence: One-sentence game description (e.g. "做一个Flappy Bird")
            answer_fn: Optional callback for interactive mode. When Clarify
                produces questions, this function is called with a list of
                [{"question": str, "node_id": str, "branches": list}].
                It should return a list of answer strings (one per question).
                If None, questions are self-answered by LLM.

        Returns:
            {"prd_document": str, "prd_summary": str, "metadata": dict}
        """
        # Step 1: Identify game with complexity detection
        game_info = self._identify_game(sentence)
        profile = _COMPLEXITY_PROFILES.get(
            game_info.complexity,
            _COMPLEXITY_PROFILES["mid-core"],
        )

        # Step 2: Research with faithfulness constraints
        research_text = self._research_game(sentence, game_info, profile)

        # Step 3: Run IG pipeline (complexity-aware)
        graph = self._run_ig_pipeline(game_info, research_text, profile)

        # Step 4: Handle ambiguities (interactive or self-answer)
        self_answered: list[dict[str, str]] = []
        user_answers: list[dict[str, str]] = []
        if graph.ambiguities:
            if answer_fn is not None:
                graph, user_answers = self._interactive_answer(
                    graph, answer_fn
                )
            else:
                graph, self_answered = self._self_answer(
                    graph, game_info, research_text
                )

        # Step 5: Generate PRD directly from research + IG
        result = self._generate_prd_direct(
            game_info, research_text, graph, profile, self_answered
        )

        # Enrich metadata
        result["metadata"]["research_source"] = (
            "web+llm" if research_text else "llm_only"
        )
        result["metadata"]["self_answered_questions"] = self_answered
        result["metadata"]["user_answered_questions"] = user_answers
        result["metadata"]["interactive_mode"] = answer_fn is not None
        result["metadata"]["input_sentence"] = sentence
        result["metadata"]["detected_game"] = game_info.game_name
        result["metadata"]["complexity"] = game_info.complexity
        result["metadata"]["genre"] = game_info.genre
        result["metadata"]["era"] = game_info.era
        result["metadata"]["core_systems"] = game_info.core_systems

        return result

    # ── Step 1: Identify ─────────────────────────────────────────────────

    def _identify_game(self, sentence: str) -> GameInfo:
        """Identify game name, complexity, genre, era, and core systems."""
        response = self._client.messages.create(
            model=self._model,
            max_tokens=512,
            temperature=0.0,
            system=(
                "You are a game design expert. Identify the game from the user's "
                "sentence and classify its design complexity. Return ONLY valid JSON."
            ),
            messages=[{"role": "user", "content": (
                f'User sentence: "{sentence}"\n\n'
                "Analyze this and return JSON:\n"
                "{\n"
                '  "game_name": "<name in English>",\n'
                '  "game_name_original": "<name as user wrote it>",\n'
                '  "language": "<zh or en>",\n'
                '  "complexity": "<arcade|casual|mid-core|hardcore>",\n'
                '  "genre": "<specific genre, e.g. vertical scrolling shooter>",\n'
                '  "era": "<original era, e.g. 1987 arcade>",\n'
                '  "core_systems": ["<list of systems the ORIGINAL game actually has, '
                'written in the SAME LANGUAGE as the user input>"]\n'
                "}\n\n"
                "Complexity guide:\n"
                "- arcade: Classic arcade games (Pac-Man, Space Invaders, 1943, Tetris, Flappy Bird). "
                "Simple controls, no progression between sessions, score-based.\n"
                "- casual: Simple modern games (Angry Birds, Candy Crush, Plants vs Zombies). "
                "Light progression, few systems.\n"
                "- mid-core: Moderate depth (Clash Royale, Stardew Valley, Hollow Knight). "
                "Multiple interlocking systems.\n"
                "- hardcore: Deep complex games (Honor of Kings/王者荣耀, League of Legends, "
                "Dark Souls, Civilization). Many systems, steep learning curve.\n\n"
                "core_systems: List ONLY systems the original game actually had. "
                "Write in the SAME language as the user's input. "
                "For Chinese input about 1943: [射击系统, 强化道具, 计分系统, BOSS战斗, 生命值]. "
                "For English input: [shooting, power-ups, scoring, boss battles, lives]. "
                "Do NOT invent systems the game never had."
            )}],
        )
        raw = response.content[0].text
        parsed = _parse_json(raw)

        return GameInfo(
            game_name=parsed.get("game_name", sentence),
            game_name_original=parsed.get("game_name_original", sentence),
            language=parsed.get("language", "zh"),
            complexity=parsed.get("complexity", "mid-core"),
            genre=parsed.get("genre", ""),
            era=parsed.get("era", ""),
            core_systems=parsed.get("core_systems", []),
        )

    # ── Step 2: Research ─────────────────────────────────────────────────

    def _research_game(
        self, sentence: str, info: GameInfo, profile: dict
    ) -> str:
        """Research game with faithfulness constraints based on complexity."""
        # Web search
        web_research = research_game(info.game_name, language=info.language)

        max_chars = profile["research_chars"]
        constraint = profile["research_constraint"]

        parts = [
            f'The user wants to make: "{sentence}"',
            f"Game: {info.game_name} ({info.era})",
            f"Genre: {info.genre}",
            f"Complexity level: {info.complexity}",
            f"Original core systems: {', '.join(info.core_systems)}",
        ]
        if web_research:
            parts.append(f"\n## Web Research (use as grounding)\n{web_research}")

        parts.append(
            f"\n## Design Constraint\n{constraint}\n\n"
            f"## Task\n"
            f"Write a game design summary in {max_chars}-{max_chars + 500} characters.\n"
            f"Cover ONLY the systems that this game actually has:\n"
            f"  {', '.join(info.core_systems)}\n\n"
            f"For each system, describe:\n"
            f"- How it works mechanically (specific, concrete)\n"
            f"- Why it's fun (the feeling, not the mechanic)\n"
            f"- Concrete numbers/thresholds where possible\n\n"
            f"DO NOT invent systems the original game never had.\n"
            f"Write in the same language as the user's input."
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            temperature=0.4,
            messages=[{"role": "user", "content": "\n".join(parts)}],
        )
        return response.content[0].text

    # ── Step 3: IG Pipeline ──────────────────────────────────────────────

    def _run_ig_pipeline(
        self, info: GameInfo, research_text: str, profile: dict
    ) -> IntentionGraph:
        """Run Connect → Expand(conditional) → Clarify."""
        dialogue = (
            f"User: I want to make a {info.genre} game based on {info.game_name}. "
            f"It is a {info.complexity}-complexity {info.era} game.\n\n"
            f"Here is the game design:\n{research_text}"
        )

        # Stage 1: Connect
        graph = self._connect.run(
            text=dialogue,
            speaker_id="user",
            speaker_label="User",
            domain="product",
        )

        # Stage 2: Expand — skip for arcade games (prevents system inflation)
        if not profile["skip_expand"] and len(graph.nodes) >= 1:
            graph = self._expand.run(graph)

        # Stage 3: Clarify
        if len(graph.transitions) >= 2:
            graph = self._clarify.run(graph)

        return graph

    # ── Step 4: Self-Answer ──────────────────────────────────────────────

    def _self_answer(
        self, graph: IntentionGraph, info: GameInfo, research_text: str
    ) -> tuple[IntentionGraph, list[dict[str, str]]]:
        """Answer ambiguities with genre and complexity awareness."""
        questions = [
            {
                "node_id": a.node_id,
                "question": a.incisive_question,
                "branches": a.branches,
            }
            for a in graph.ambiguities
            if a.incisive_question
        ]

        if not questions:
            return graph, []

        questions_text = "\n".join(
            f"{i+1}. {q['question']}" for i, q in enumerate(questions)
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            temperature=0.3,
            system=(
                f"You are a game designer making a {info.genre} game "
                f"({info.complexity} complexity, {info.era}).\n\n"
                f"Answer design questions with these principles:\n"
                f"1. Stay faithful to the original game's design philosophy\n"
                f"2. For arcade games: prefer simplicity over depth\n"
                f"3. Focus on concrete design tradeoffs, not abstract preferences\n"
                f"4. When in doubt, choose the option closer to the original game\n\n"
                f"Return ONLY valid JSON."
            ),
            messages=[{"role": "user", "content": (
                f"## Game: {info.game_name} ({info.era})\n"
                f"## Complexity: {info.complexity}\n"
                f"## Original systems: {', '.join(info.core_systems)}\n\n"
                f"## Research\n{research_text[:2000]}\n\n"
                f"## Design Questions\n{questions_text}\n\n"
                "Return JSON:\n"
                '{"answers": [\n'
                '  {"question_number": 1, "answer": "<concise answer>", '
                '"chosen_branch": "<branch_id if applicable>"}\n'
                "]}"
            )}],
        )

        raw = response.content[0].text
        parsed = _parse_json(raw)
        answers = parsed.get("answers", [])

        self_answered = []
        for q, a in zip(questions, answers):
            self_answered.append({
                "question": q["question"],
                "answer": a.get("answer", ""),
            })
            chosen = a.get("chosen_branch", "")
            if chosen and q["branches"]:
                graph = _boost_branch(graph, q["node_id"], chosen)

        # Clear resolved ambiguities
        graph = IntentionGraph(
            nodes=graph.nodes,
            transitions=graph.transitions,
            end_goal=graph.end_goal,
            dna_profile_id=graph.dna_profile_id,
            completed_path=graph.completed_path,
            evolution_history=graph.evolution_history,
            ambiguities=[],
            summary=graph.summary,
        )

        return graph, self_answered

    def _interactive_answer(
        self,
        graph: IntentionGraph,
        answer_fn: Callable[[list[dict[str, str]]], list[str]],
    ) -> tuple[IntentionGraph, list[dict[str, str]]]:
        """Present questions to user via callback, apply their answers."""
        questions = [
            {
                "question": a.incisive_question,
                "node_id": a.node_id,
                "branches": a.branches,
            }
            for a in graph.ambiguities
            if a.incisive_question
        ]

        if not questions:
            return graph, []

        # Call user-provided function
        user_responses = answer_fn(questions)

        answered = []
        for q, response_text in zip(questions, user_responses):
            answered.append({
                "question": q["question"],
                "answer": response_text,
            })
            # If user's answer matches a branch name, boost it
            if q["branches"]:
                # Try to find the best matching branch
                best_branch = q["branches"][0]  # default to first
                for branch_id in q["branches"]:
                    # Find node text for this branch
                    branch_node = next(
                        (n for n in graph.nodes if n.id == branch_id), None
                    )
                    if branch_node and branch_node.text.lower() in response_text.lower():
                        best_branch = branch_id
                        break
                graph = _boost_branch(graph, q["node_id"], best_branch)

        # Clear resolved ambiguities
        graph = IntentionGraph(
            nodes=graph.nodes,
            transitions=graph.transitions,
            end_goal=graph.end_goal,
            dna_profile_id=graph.dna_profile_id,
            completed_path=graph.completed_path,
            evolution_history=graph.evolution_history,
            ambiguities=[],
            summary=graph.summary,
        )

        return graph, answered

    # ── Step 5: Direct PRD Generation ────────────────────────────────────

    def _generate_prd_direct(
        self,
        info: GameInfo,
        research_text: str,
        graph: IntentionGraph,
        profile: dict,
        self_answered: list[dict[str, str]],
    ) -> dict[str, Any]:
        """Generate PRD directly from research + IntentionGraph.

        Replaces _synthesize_conversation + PrdGenerator.generate_sync,
        eliminating 4 redundant LLM calls (synthesize + PrdGenerator's
        internal connect + expand + generate).
        """
        ig_context = _graph_to_context(graph)

        # Build user prompt with all context
        lang = "Chinese (中文)" if info.language.startswith("zh") else "English"
        max_systems = profile["max_systems"]

        # Format core systems as if user described them
        core_systems_text = "\n".join(
            f"- {s}" for s in info.core_systems
        )

        user_parts = [
            f"## Game\n{info.game_name} ({info.genre}, {info.era})",
            f"Complexity: {info.complexity}",
            f"\n## User's Original Request\n\"{info.game_name_original}\"",
            (
                f"\n## What the User Described (user-stated systems)\n"
                f"The user wants to make {info.game_name}. "
                f"They explicitly described these game systems:\n{core_systems_text}\n\n"
                f"CRITICAL: Every system listed above is user-stated. "
                f"When writing Section 3, these systems MUST NOT be tagged [INFERRED]. "
                f"Only tag a system [INFERRED] if it does NOT appear in this list "
                f"and you added it yourself."
            ),
            f"\n## Game Design Research\n{research_text}",
        ]

        if self_answered:
            user_parts.append("\n## Design Decisions (Q&A)")
            for qa in self_answered:
                user_parts.append(f"Q: {qa['question']}\nA: {qa['answer']}")

        if ig_context:
            user_parts.append(f"\n## Intention Graph Analysis\n{ig_context}")

        min_chars = profile.get("min_prd_chars", 6000)
        user_parts.append(
            f"\n## Constraints\n"
            f"- Write the entire PRD in {lang}\n"
            f"- EXACTLY {max_systems} game systems in Section 3 "
            f"(no more, no fewer)\n"
            f"- Only include systems the original game actually has\n"
            f"- Every 设计考量 MUST contain at least one '?' question\n\n"
            f"## Length Requirements (CRITICAL)\n"
            f"- Section 1 (游戏总览): ~800-1200 chars\n"
            f"- Section 2 (核心游戏循环): ~1000-1500 chars\n"
            f"- Section 3 (游戏系统): Each system ~500-800 chars "
            f"with 如何运作/为何感觉良好/设计考量/如何连接 all filled\n"
            f"- Section 4 (美术与音效风格): ~1200-1800 chars, all 8 subsections\n"
            f"- TOTAL MINIMUM: {min_chars} characters. Write richly."
        )

        user_message = "\n".join(user_parts)

        # Supplementary instruction for direct mode: override [INFERRED]
        # rule since there's no conversation to check against
        direct_mode_supplement = (
            "\n\n## DIRECT MODE OVERRIDE\n"
            "This PRD is being generated from structured design input, "
            "not a conversation. The [INFERRED] rule should be applied as follows:\n"
            "- Systems listed under 'What the User Described' are user-stated → "
            "do NOT tag them [INFERRED], even if the system name in the PRD "
            "differs slightly (e.g., '生命值' → '生命值系统' is the same).\n"
            "- Only tag [INFERRED] for systems you add that are NOT listed "
            "in the user's described systems.\n"
            "- IMPORTANT: Write at least 6000 characters. Each system in "
            "Section 3 needs 400-600 characters of detailed description."
        )

        prd_max_tokens = profile.get("prd_max_tokens", 8000)
        response = self._client.messages.create(
            model=self._model,
            max_tokens=prd_max_tokens,
            temperature=0.7,
            system=_PRD_SYSTEM_PROMPT + direct_mode_supplement,
            messages=[{"role": "user", "content": user_message}],
        )
        raw = response.content[0].text

        prd_document, prd_summary = _parse_prd_response(raw)

        # Build metadata compatible with PrdGenerator output
        core_intention = ""
        num_intentions = len(graph.nodes) if graph.nodes else 0
        if graph.end_goal and graph.nodes:
            end_node = next(
                (n for n in graph.nodes if n.id == graph.end_goal), None
            )
            if end_node:
                core_intention = end_node.text

        metadata = {
            "core_intention": core_intention,
            "num_intentions": num_intentions,
            "num_facts": len(info.core_systems),
            "ig_available": bool(graph.nodes),
            "language": info.language,
            "model": self._model,
            "pipeline": "direct",  # distinguishes from v2's PrdGenerator path
        }

        return {
            "prd_document": prd_document,
            "prd_summary": prd_summary,
            "metadata": metadata,
        }

    # ── Legacy: Synthesize Conversation (kept for reference) ──────────

    def _synthesize_conversation(
        self,
        info: GameInfo,
        research_text: str,
        graph: IntentionGraph,
        profile: dict,
    ) -> tuple[list[dict[str, str]], list[str]]:
        """Synthesize honest conversation that separates user intent from research."""
        graph_nodes = "\n".join(
            f"- {n.text} (confidence={n.confidence:.2f})"
            for n in graph.nodes
        )
        end_goal_text = ""
        if graph.end_goal:
            end_node = next(
                (n for n in graph.nodes if n.id == graph.end_goal), None
            )
            if end_node:
                end_goal_text = f"Core goal: {end_node.text}"

        lang_instruction = (
            "Chinese (中文)" if info.language.startswith("zh") else "English"
        )
        max_systems = profile["max_systems"]
        turns = profile["conversation_turns"]

        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            temperature=0.5,
            system=(
                "You are generating a synthetic game design conversation.\n\n"
                "CRITICAL RULES:\n"
                "1. The User's FIRST message must be EXACTLY their original sentence "
                "(this is the only thing they actually said).\n"
                "2. After the first message, the User expands based on the research, "
                "but ONLY discusses systems that the original game actually has.\n"
                "3. The Host asks probing questions about specific mechanics, "
                "not about adding new systems.\n"
                "4. Do NOT have the User describe systems that the original game "
                "never had (no invented RPG/progression systems for arcade games).\n"
                "5. Keep the conversation scope proportional to the game's complexity.\n"
                "6. IMPORTANT: The User must mention ALL core systems listed in the "
                "constraints. Every system should appear in at least one User message. "
                "This ensures the PRD doesn't mark core systems as [INFERRED].\n\n"
                "Return ONLY valid JSON."
            ),
            messages=[{"role": "user", "content": (
                f"## Original User Input (the ONLY thing the user actually said)\n"
                f'"{info.game_name_original}"\n\n'
                f"## Game Info\n"
                f"Game: {info.game_name} ({info.era})\n"
                f"Genre: {info.genre}\n"
                f"Complexity: {info.complexity}\n"
                f"Original core systems: {', '.join(info.core_systems)}\n\n"
                f"## Research (use to flesh out User responses)\n"
                f"{research_text[:2500]}\n\n"
                f"## Intention Graph\n{graph_nodes}\n"
                f"{end_goal_text}\n\n"
                f"## Constraints\n"
                f"- Generate {turns} turns\n"
                f"- Maximum {max_systems} game systems discussed\n"
                f"- User's first message MUST be: \"{info.game_name_original}\"\n"
                f"- Write in {lang_instruction}\n\n"
                f"## CHECKLIST: User MUST mention ALL of these systems\n"
                + "".join(
                    f"- [ ] {sys}\n" for sys in info.core_systems
                )
                + "\nEvery system above must appear in at least one User message. "
                f"This prevents the PRD from marking core systems as [INFERRED].\n\n"
                f"## Facts\n"
                f"Extract {max_systems + 2}-{max_systems + 5} structured facts. "
                f"Only include facts about systems the original game has.\n\n"
                f"Return JSON:\n"
                '{{\n'
                '  "conversation": [\n'
                '    {{"role": "user", "content": "..."}},\n'
                '    {{"role": "host", "content": "..."}}\n'
                '  ],\n'
                '  "facts": ["fact 1", "fact 2"]\n'
                '}}'
            )}],
        )

        raw = response.content[0].text
        parsed = _parse_json(raw)

        conversation = parsed.get("conversation", [])
        facts = parsed.get("facts", [])

        # Fallback
        if not conversation:
            conversation = [
                {"role": "user", "content": info.game_name_original},
                {"role": "host", "content": "Tell me more about the game design."},
                {"role": "user", "content": research_text[:2000]},
            ]

        if not facts:
            facts = [f"Game: {info.game_name} ({info.genre})"]

        return conversation, facts


# ── Helpers ──────────────────────────────────────────────────────────────────

def _boost_branch(
    graph: IntentionGraph, node_id: str, chosen_branch: str
) -> IntentionGraph:
    """Boost probability of chosen branch transition, lower others."""
    new_transitions = []
    for t in graph.transitions:
        if t.from_id == node_id:
            if t.to_id == chosen_branch:
                new_transitions.append(Transition(
                    from_id=t.from_id,
                    to_id=t.to_id,
                    base_probability=t.base_probability,
                    dna_adjusted_probability=min(
                        1.0, t.dna_adjusted_probability + 0.3
                    ),
                    relation=t.relation,
                    confidence=t.confidence,
                ))
            else:
                new_transitions.append(Transition(
                    from_id=t.from_id,
                    to_id=t.to_id,
                    base_probability=t.base_probability,
                    dna_adjusted_probability=max(
                        0.0, t.dna_adjusted_probability - 0.15
                    ),
                    relation=t.relation,
                    confidence=t.confidence,
                ))
        else:
            new_transitions.append(t)

    return IntentionGraph(
        nodes=graph.nodes,
        transitions=new_transitions,
        end_goal=graph.end_goal,
        dna_profile_id=graph.dna_profile_id,
        completed_path=graph.completed_path,
        evolution_history=graph.evolution_history,
        ambiguities=graph.ambiguities,
        summary=graph.summary,
    )


def _parse_json(raw: str) -> dict:
    """Robustly parse JSON from LLM response."""
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    start = raw.find("{")
    last = raw.rfind("}")
    if start != -1 and last != -1:
        try:
            return json.loads(raw[start:last + 1])
        except json.JSONDecodeError:
            pass

    return {}
