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
from dataclasses import dataclass, field
from typing import Any

import anthropic

from intention_graph.connect import Connect
from intention_graph.expand import Expand
from intention_graph.clarify import Clarify
from intention_graph.models import IntentionGraph, Transition
from intention_graph.prd_generator import PrdGenerator
from intention_graph.web_search import research_game


# ── Complexity profiles ─────────────────────────────────────────────────────

_COMPLEXITY_PROFILES = {
    "arcade": {
        "max_systems": 4,
        "skip_expand": True,
        "research_chars": 1500,
        "conversation_turns": "6-8",
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
        "max_systems": 5,
        "skip_expand": False,
        "research_chars": 2000,
        "conversation_turns": "8-10",
        "research_constraint": (
            "This is a casual game. Keep systems lightweight.\n"
            "Only include progression systems that are simple and natural.\n"
            "Avoid over-engineering with complex meta-game loops."
        ),
    },
    "mid-core": {
        "max_systems": 7,
        "skip_expand": False,
        "research_chars": 3000,
        "conversation_turns": "10-12",
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

    def generate(self, sentence: str) -> dict[str, Any]:
        """Full pipeline: sentence → PRD.

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

        # Step 4: Self-answer ambiguities (genre-aware)
        self_answered: list[dict[str, str]] = []
        if graph.ambiguities:
            graph, self_answered = self._self_answer(
                graph, game_info, research_text
            )

        # Step 5: Synthesize honest conversation
        conversation, facts = self._synthesize_conversation(
            game_info, research_text, graph, profile
        )

        # Step 6: Generate PRD via existing PrdGenerator
        game = SimpleGame(facts=facts)
        session_info = {
            "uid": "one_sentence",
            "session_id": "one_sentence",
            "language": game_info.language,
        }
        result = self._prd_generator.generate_sync(
            game=game,
            conversation_history=conversation,
            session_info=session_info,
        )

        # Enrich metadata
        result["metadata"]["research_source"] = (
            "web+llm" if research_text else "llm_only"
        )
        result["metadata"]["self_answered_questions"] = self_answered
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
                '  "core_systems": ["<list of systems the ORIGINAL game actually has>"]\n'
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
                "For 1943: [shooting, power-ups, scoring, boss battles, lives/energy]. "
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

    # ── Step 5: Synthesize Conversation ──────────────────────────────────

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
                f"- Only discuss systems from: {', '.join(info.core_systems)}\n"
                f"- Write in {lang_instruction}\n\n"
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
