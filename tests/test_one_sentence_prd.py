# tests/test_one_sentence_prd.py
"""Tests for OneSentencePrd: unit tests (mocked) + integration tests (API).

Unit tests verify pipeline orchestration logic without LLM calls.
Integration tests require ANTHROPIC_API_KEY and are slow (~2-3 min each).
"""

import json
import os
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from intention_graph.models import (
    ActionNode,
    Ambiguity,
    IntentionGraph,
    Transition,
)
from intention_graph.one_sentence_prd import (
    GameInfo,
    OneSentencePrd,
    SimpleGame,
    _boost_branch,
    _parse_json,
    _COMPLEXITY_PROFILES,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


def _make_graph(
    num_nodes: int = 3,
    num_transitions: int = 2,
    ambiguities: list[Ambiguity] | None = None,
) -> IntentionGraph:
    """Create a minimal IntentionGraph for testing."""
    nodes = [
        ActionNode(
            id=f"int_{i+1:03d}",
            text=f"intention {i+1}",
            domain="product",
            source="expressed",
            status="pending",
            confidence=0.8,
            specificity=0.6,
        )
        for i in range(num_nodes)
    ]
    transitions = [
        Transition(
            from_id=f"int_{i+1:03d}",
            to_id=f"int_{i+2:03d}",
            base_probability=0.7,
            dna_adjusted_probability=0.7,
            relation="next_step",
            confidence=0.8,
        )
        for i in range(min(num_transitions, num_nodes - 1))
    ]
    return IntentionGraph(
        nodes=nodes,
        transitions=transitions,
        end_goal="int_001",
        ambiguities=ambiguities or [],
        summary="test graph",
    )


def _mock_llm_response(text: str) -> MagicMock:
    """Create a mock anthropic response."""
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = text
    mock_response.content = [mock_content]
    return mock_response


# ── Unit Tests: _parse_json ──────────────────────────────────────────────────


def test_parse_json_valid():
    assert _parse_json('{"a": 1}') == {"a": 1}


def test_parse_json_with_markdown_fences():
    raw = '```json\n{"key": "value"}\n```'
    assert _parse_json(raw) == {"key": "value"}


def test_parse_json_embedded_in_text():
    raw = 'Here is the result: {"x": 42} end'
    assert _parse_json(raw) == {"x": 42}


def test_parse_json_invalid_returns_empty():
    assert _parse_json("not json at all") == {}


def test_parse_json_empty_string():
    assert _parse_json("") == {}


# ── Unit Tests: _boost_branch ────────────────────────────────────────────────


def test_boost_branch_increases_chosen():
    graph = _make_graph(3, 2)
    # Add a second transition from int_001
    graph.transitions.append(
        Transition(
            from_id="int_001",
            to_id="int_003",
            base_probability=0.5,
            dna_adjusted_probability=0.5,
            relation="alternative",
            confidence=0.7,
        )
    )
    boosted = _boost_branch(graph, "int_001", "int_002")
    # Find the boosted transition
    chosen = next(
        t for t in boosted.transitions
        if t.from_id == "int_001" and t.to_id == "int_002"
    )
    other = next(
        t for t in boosted.transitions
        if t.from_id == "int_001" and t.to_id == "int_003"
    )
    assert chosen.dna_adjusted_probability == 1.0  # 0.7 + 0.3, clamped
    assert other.dna_adjusted_probability == 0.35  # 0.5 - 0.15


def test_boost_branch_clamps_to_bounds():
    graph = _make_graph(2, 1)
    graph.transitions[0] = Transition(
        from_id="int_001",
        to_id="int_002",
        base_probability=0.9,
        dna_adjusted_probability=0.9,
        relation="next_step",
        confidence=0.8,
    )
    boosted = _boost_branch(graph, "int_001", "int_002")
    t = boosted.transitions[0]
    assert t.dna_adjusted_probability == 1.0  # clamped to max


def test_boost_branch_unrelated_transitions_unchanged():
    graph = _make_graph(4, 3)
    boosted = _boost_branch(graph, "int_001", "int_002")
    # Transition from int_002 → int_003 should be unchanged
    t23 = next(
        t for t in boosted.transitions
        if t.from_id == "int_002" and t.to_id == "int_003"
    )
    assert t23.dna_adjusted_probability == 0.7  # unchanged


# ── Unit Tests: Complexity Profiles ──────────────────────────────────────────


def test_complexity_profiles_all_defined():
    assert "arcade" in _COMPLEXITY_PROFILES
    assert "casual" in _COMPLEXITY_PROFILES
    assert "mid-core" in _COMPLEXITY_PROFILES
    assert "hardcore" in _COMPLEXITY_PROFILES


def test_arcade_profile_skips_expand():
    assert _COMPLEXITY_PROFILES["arcade"]["skip_expand"] is True


def test_non_arcade_profiles_allow_expand():
    for level in ["casual", "mid-core", "hardcore"]:
        assert _COMPLEXITY_PROFILES[level]["skip_expand"] is False


def test_complexity_max_systems_increase():
    levels = ["arcade", "casual", "mid-core", "hardcore"]
    max_systems = [_COMPLEXITY_PROFILES[l]["max_systems"] for l in levels]
    # Each level should allow >= the previous
    for i in range(1, len(max_systems)):
        assert max_systems[i] >= max_systems[i - 1]


# ── Unit Tests: GameInfo ─────────────────────────────────────────────────────


def test_game_info_creation():
    info = GameInfo(
        game_name="Pac-Man",
        game_name_original="吃豆人",
        language="zh",
        complexity="arcade",
        genre="maze chase",
        era="1980 arcade",
        core_systems=["movement", "pellets", "ghosts", "power-ups"],
    )
    assert info.complexity == "arcade"
    assert len(info.core_systems) == 4


def test_simple_game_defaults():
    game = SimpleGame()
    assert game.facts == []
    game2 = SimpleGame(facts=["type: shooter"])
    assert len(game2.facts) == 1


# ── Unit Tests: Pipeline Orchestration (mocked LLM) ─────────────────────────


class TestPipelineOrchestration:
    """Test that the pipeline correctly routes based on complexity."""

    def _make_prd(self) -> OneSentencePrd:
        """Create OneSentencePrd with mocked client."""
        with patch("intention_graph.one_sentence_prd.anthropic.Anthropic"):
            with patch("intention_graph.one_sentence_prd.Connect"):
                with patch("intention_graph.one_sentence_prd.Expand"):
                    with patch("intention_graph.one_sentence_prd.Clarify"):
                        with patch("intention_graph.one_sentence_prd.PrdGenerator"):
                            prd = OneSentencePrd(api_key="test-key")
        return prd

    def test_identify_game_parses_response(self):
        prd = self._make_prd()
        prd._client.messages.create.return_value = _mock_llm_response(
            json.dumps({
                "game_name": "1943: The Battle of Midway",
                "game_name_original": "1943模拟游戏",
                "language": "zh",
                "complexity": "arcade",
                "genre": "vertical scrolling shooter",
                "era": "1987 arcade",
                "core_systems": ["shooting", "power-ups", "boss battles"],
            })
        )
        info = prd._identify_game("请帮我生成一个1943模拟游戏")
        assert info.game_name == "1943: The Battle of Midway"
        assert info.complexity == "arcade"
        assert info.language == "zh"
        assert "shooting" in info.core_systems

    def test_identify_game_handles_malformed_json(self):
        prd = self._make_prd()
        prd._client.messages.create.return_value = _mock_llm_response(
            "not valid json"
        )
        info = prd._identify_game("test game")
        # Should fallback gracefully
        assert info.game_name == "test game"
        assert info.complexity == "mid-core"  # default

    def test_run_ig_pipeline_skips_expand_for_arcade(self):
        prd = self._make_prd()
        graph = _make_graph(3, 2)
        prd._connect.run.return_value = graph
        prd._clarify.run.return_value = graph

        info = GameInfo(
            game_name="1943",
            game_name_original="1943",
            language="zh",
            complexity="arcade",
            genre="shooter",
            era="1987",
            core_systems=["shooting"],
        )
        profile = _COMPLEXITY_PROFILES["arcade"]

        result = prd._run_ig_pipeline(info, "research text", profile)

        prd._connect.run.assert_called_once()
        prd._expand.run.assert_not_called()  # skipped for arcade!
        prd._clarify.run.assert_called_once()
        assert result is not None

    def test_run_ig_pipeline_runs_expand_for_midcore(self):
        prd = self._make_prd()
        graph = _make_graph(3, 2)
        prd._connect.run.return_value = graph
        prd._expand.run.return_value = graph
        prd._clarify.run.return_value = graph

        info = GameInfo(
            game_name="Hollow Knight",
            game_name_original="空洞骑士",
            language="zh",
            complexity="mid-core",
            genre="metroidvania",
            era="2017",
            core_systems=["combat", "exploration"],
        )
        profile = _COMPLEXITY_PROFILES["mid-core"]

        prd._run_ig_pipeline(info, "research text", profile)

        prd._expand.run.assert_called_once()  # runs for mid-core

    def test_self_answer_skips_when_no_questions(self):
        prd = self._make_prd()
        graph = _make_graph(3, 2, ambiguities=[])

        info = GameInfo(
            game_name="test",
            game_name_original="test",
            language="en",
            complexity="arcade",
            genre="test",
            era="test",
        )
        result_graph, answered = prd._self_answer(graph, info, "research")

        prd._client.messages.create.assert_not_called()
        assert answered == []

    def test_interactive_answer_calls_callback(self):
        prd = self._make_prd()
        ambiguities = [
            Ambiguity(
                node_id="int_001",
                branches=["int_002", "int_003"],
                incisive_question="Do you prefer A or B?",
                information_gain=0.8,
            )
        ]
        graph = _make_graph(3, 2, ambiguities=ambiguities)

        # Mock user callback
        user_answers = ["I prefer approach A"]
        answer_fn = MagicMock(return_value=user_answers)

        result_graph, answered = prd._interactive_answer(graph, answer_fn)

        answer_fn.assert_called_once()
        assert len(answered) == 1
        assert answered[0]["question"] == "Do you prefer A or B?"
        assert answered[0]["answer"] == "I prefer approach A"
        assert result_graph.ambiguities == []  # cleared

    def test_interactive_answer_skips_when_no_questions(self):
        prd = self._make_prd()
        graph = _make_graph(3, 2, ambiguities=[])

        answer_fn = MagicMock(return_value=[])
        result_graph, answered = prd._interactive_answer(graph, answer_fn)

        answer_fn.assert_not_called()
        assert answered == []

    def test_generate_uses_answer_fn_when_provided(self):
        """Verify generate() routes to interactive when answer_fn given."""
        prd = self._make_prd()

        # Mock _identify_game to return a game info
        prd._identify_game = MagicMock(return_value=GameInfo(
            game_name="Test",
            game_name_original="测试",
            language="zh",
            complexity="mid-core",
            genre="test",
            era="2024",
            core_systems=["a", "b"],
        ))
        prd._research_game = MagicMock(return_value="research text")

        # Graph with ambiguities
        graph_with_amb = _make_graph(3, 2, ambiguities=[
            Ambiguity(
                node_id="int_001",
                branches=["int_002"],
                incisive_question="Question?",
                information_gain=0.5,
            )
        ])
        prd._run_ig_pipeline = MagicMock(return_value=graph_with_amb)
        prd._synthesize_conversation = MagicMock(
            return_value=([{"role": "user", "content": "hi"}], ["fact1"])
        )
        prd._prd_generator.generate_sync.return_value = {
            "prd_document": "doc",
            "prd_summary": "sum",
            "metadata": {"ig_available": True},
        }

        answer_fn = MagicMock(return_value=["My answer"])
        result = prd.generate("测试", answer_fn=answer_fn)

        answer_fn.assert_called_once()
        assert result["metadata"]["interactive_mode"] is True
        assert len(result["metadata"]["user_answered_questions"]) == 1

    def test_generate_metadata_non_interactive(self):
        """Verify metadata flags when not using interactive mode."""
        prd = self._make_prd()

        prd._identify_game = MagicMock(return_value=GameInfo(
            game_name="Test",
            game_name_original="测试",
            language="zh",
            complexity="arcade",
            genre="test",
            era="2024",
            core_systems=["a"],
        ))
        prd._research_game = MagicMock(return_value="research")
        prd._run_ig_pipeline = MagicMock(return_value=_make_graph(2, 1))
        prd._synthesize_conversation = MagicMock(
            return_value=([{"role": "user", "content": "hi"}], ["fact1"])
        )
        prd._prd_generator.generate_sync.return_value = {
            "prd_document": "doc",
            "prd_summary": "sum",
            "metadata": {"ig_available": True},
        }

        result = prd.generate("测试")

        assert result["metadata"]["interactive_mode"] is False
        assert result["metadata"]["user_answered_questions"] == []

    def test_self_answer_calls_llm_when_ambiguities_exist(self):
        prd = self._make_prd()
        ambiguities = [
            Ambiguity(
                node_id="int_001",
                branches=["int_002", "int_003"],
                incisive_question="Which approach do you prefer?",
                information_gain=0.8,
            )
        ]
        graph = _make_graph(3, 2, ambiguities=ambiguities)

        prd._client.messages.create.return_value = _mock_llm_response(
            json.dumps({
                "answers": [
                    {
                        "question_number": 1,
                        "answer": "Approach A",
                        "chosen_branch": "int_002",
                    }
                ]
            })
        )

        info = GameInfo(
            game_name="test",
            game_name_original="test",
            language="en",
            complexity="mid-core",
            genre="test",
            era="test",
        )
        result_graph, answered = prd._self_answer(graph, info, "research")

        prd._client.messages.create.assert_called_once()
        assert len(answered) == 1
        assert answered[0]["question"] == "Which approach do you prefer?"
        assert result_graph.ambiguities == []  # cleared

    def test_synthesize_conversation_returns_valid_structure(self):
        prd = self._make_prd()
        prd._client.messages.create.return_value = _mock_llm_response(
            json.dumps({
                "conversation": [
                    {"role": "user", "content": "I want a game"},
                    {"role": "host", "content": "Tell me more"},
                ],
                "facts": ["fact 1", "fact 2"],
            })
        )

        info = GameInfo(
            game_name="TestGame",
            game_name_original="测试游戏",
            language="zh",
            complexity="arcade",
            genre="test",
            era="test",
            core_systems=["system1"],
        )
        profile = _COMPLEXITY_PROFILES["arcade"]
        graph = _make_graph(2, 1)

        conv, facts = prd._synthesize_conversation(
            info, "research text", graph, profile
        )

        assert len(conv) == 2
        assert conv[0]["role"] == "user"
        assert len(facts) == 2

    def test_synthesize_conversation_fallback_on_bad_json(self):
        prd = self._make_prd()
        prd._client.messages.create.return_value = _mock_llm_response(
            "totally not json"
        )

        info = GameInfo(
            game_name="TestGame",
            game_name_original="测试游戏",
            language="zh",
            complexity="arcade",
            genre="test",
            era="test",
            core_systems=["system1"],
        )
        profile = _COMPLEXITY_PROFILES["arcade"]
        graph = _make_graph(2, 1)

        conv, facts = prd._synthesize_conversation(
            info, "research text", graph, profile
        )

        # Should use fallback
        assert len(conv) >= 2
        assert len(facts) >= 1


# ── Unit Tests: Web Search ───────────────────────────────────────────────────


class TestWebSearch:
    """Test web_search module graceful degradation."""

    def test_search_game_returns_list(self):
        from intention_graph.web_search import search_game
        # May return [] if duckduckgo-search not installed — that's OK
        results = search_game("nonexistent game xyz", max_results=2)
        assert isinstance(results, list)

    def test_fetch_wikipedia_returns_string_or_none(self):
        from intention_graph.web_search import fetch_wikipedia
        result = fetch_wikipedia("Python_(programming_language)")
        # Should return a string (Wikipedia article exists) or None
        assert result is None or isinstance(result, str)

    def test_fetch_wikipedia_nonexistent_returns_none(self):
        from intention_graph.web_search import fetch_wikipedia
        result = fetch_wikipedia("XYZ_NONEXISTENT_PAGE_12345")
        assert result is None

    def test_research_game_returns_string(self):
        from intention_graph.web_search import research_game
        result = research_game("Pac-Man", language="en")
        assert isinstance(result, str)

    def test_research_game_chinese_lang(self):
        from intention_graph.web_search import research_game
        result = research_game("Pac-Man", language="zh")
        assert isinstance(result, str)

    def test_search_result_dataclass(self):
        from intention_graph.web_search import SearchResult
        sr = SearchResult(title="Test", snippet="A snippet", url="https://example.com")
        assert sr.title == "Test"
        assert sr.url == "https://example.com"


# ── Unit Tests: Full generate() orchestration ────────────────────────────────


class TestGenerateOrchestration:
    """Test that generate() wires all steps correctly."""

    def _make_prd_with_mocks(self) -> OneSentencePrd:
        """Create fully mocked OneSentencePrd."""
        with patch("intention_graph.one_sentence_prd.anthropic.Anthropic"):
            with patch("intention_graph.one_sentence_prd.Connect"):
                with patch("intention_graph.one_sentence_prd.Expand"):
                    with patch("intention_graph.one_sentence_prd.Clarify"):
                        with patch("intention_graph.one_sentence_prd.PrdGenerator"):
                            prd = OneSentencePrd(api_key="test-key")
        return prd

    @patch("intention_graph.one_sentence_prd.research_game")
    def test_generate_full_pipeline_arcade(self, mock_research):
        """Verify arcade path: skip expand, add complexity to metadata."""
        mock_research.return_value = "mock web research"

        prd = self._make_prd_with_mocks()

        # Mock _identify_game
        prd._client.messages.create.side_effect = [
            # identify call
            _mock_llm_response(json.dumps({
                "game_name": "Pac-Man",
                "game_name_original": "吃豆人",
                "language": "zh",
                "complexity": "arcade",
                "genre": "maze chase",
                "era": "1980 arcade",
                "core_systems": ["movement", "pellets", "ghosts"],
            })),
            # research call
            _mock_llm_response("Pac-Man is a classic arcade game..."),
            # synthesize call
            _mock_llm_response(json.dumps({
                "conversation": [
                    {"role": "user", "content": "吃豆人"},
                    {"role": "host", "content": "好的"},
                ],
                "facts": ["type: maze chase"],
            })),
        ]

        # Mock IG pipeline
        graph = _make_graph(3, 2)
        prd._connect.run.return_value = graph
        prd._clarify.run.return_value = graph

        # Mock PrdGenerator
        prd._prd_generator.generate_sync.return_value = {
            "prd_document": "mock PRD",
            "prd_summary": "mock summary",
            "metadata": {"ig_available": True, "num_intentions": 3},
        }

        result = prd.generate("吃豆人")

        # Verify orchestration
        prd._expand.run.assert_not_called()  # arcade → skip
        assert result["metadata"]["complexity"] == "arcade"
        assert result["metadata"]["detected_game"] == "Pac-Man"
        assert result["metadata"]["research_source"] == "web+llm"

    @patch("intention_graph.one_sentence_prd.research_game")
    def test_generate_runs_expand_for_hardcore(self, mock_research):
        """Verify hardcore path runs expand."""
        mock_research.return_value = ""

        prd = self._make_prd_with_mocks()

        prd._client.messages.create.side_effect = [
            _mock_llm_response(json.dumps({
                "game_name": "Honor of Kings",
                "game_name_original": "王者荣耀",
                "language": "zh",
                "complexity": "hardcore",
                "genre": "MOBA",
                "era": "2015 mobile",
                "core_systems": ["heroes", "combat", "items"],
            })),
            _mock_llm_response("Honor of Kings is a MOBA..."),
            _mock_llm_response(json.dumps({
                "conversation": [
                    {"role": "user", "content": "王者荣耀"},
                    {"role": "host", "content": "好的"},
                ],
                "facts": ["type: MOBA"],
            })),
        ]

        graph = _make_graph(5, 4)
        prd._connect.run.return_value = graph
        prd._expand.run.return_value = graph
        prd._clarify.run.return_value = graph

        prd._prd_generator.generate_sync.return_value = {
            "prd_document": "mock PRD",
            "prd_summary": "mock summary",
            "metadata": {"ig_available": True, "num_intentions": 5},
        }

        result = prd.generate("王者荣耀")

        prd._expand.run.assert_called_once()  # hardcore → runs expand
        assert result["metadata"]["complexity"] == "hardcore"
        # research_source is "web+llm" because research_text (LLM output) is truthy
        assert result["metadata"]["research_source"] == "web+llm"


# ── Integration Tests (require API key) ──────────────────────────────────────


@pytest.fixture
def one_sentence_prd() -> OneSentencePrd:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return OneSentencePrd(api_key=api_key)


@pytest.mark.slow
def test_integration_arcade_1943(one_sentence_prd: OneSentencePrd):
    """Full pipeline test for arcade game."""
    result = one_sentence_prd.generate("请帮我生成一个1943模拟游戏")

    # PRD structure
    assert result["prd_document"], "PRD document should not be empty"
    assert result["prd_summary"], "PRD summary should not be empty"

    # All 4 mandatory sections
    doc = result["prd_document"]
    assert "游戏总览" in doc
    assert "核心游戏循环" in doc
    assert "游戏系统" in doc
    assert "美术与音效风格" in doc

    # Metadata
    meta = result["metadata"]
    assert meta["ig_available"] is True
    assert meta["num_intentions"] >= 3
    assert meta["complexity"] == "arcade"
    assert meta["language"] == "zh"
    assert meta["research_source"] in ("web+llm", "llm_only")

    # Faithfulness: should NOT contain modern systems
    doc_lower = doc.lower()
    assert "技能树" not in doc or "[INFERRED]" in doc  # no skill tree
    assert "装备系统" not in doc_lower  # no equipment system


@pytest.mark.slow
def test_integration_casual_flappy(one_sentence_prd: OneSentencePrd):
    """Full pipeline test for casual game."""
    result = one_sentence_prd.generate("做一个Flappy Bird")

    assert result["prd_document"]
    assert "游戏总览" in result["prd_document"]

    meta = result["metadata"]
    assert meta["ig_available"] is True
    assert meta["complexity"] in ("arcade", "casual")  # either is acceptable
    assert meta["language"] == "zh"


@pytest.mark.slow
def test_integration_hardcore_kings(one_sentence_prd: OneSentencePrd):
    """Full pipeline test for hardcore game."""
    result = one_sentence_prd.generate("王者荣耀")

    assert result["prd_document"]
    doc = result["prd_document"]
    assert "游戏总览" in doc
    assert "核心游戏循环" in doc

    meta = result["metadata"]
    assert meta["ig_available"] is True
    assert meta["complexity"] == "hardcore"
    assert meta["num_intentions"] >= 5  # complex game should have many
