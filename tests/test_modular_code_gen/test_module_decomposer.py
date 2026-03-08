"""Tests for module decomposer."""

import json
from unittest.mock import MagicMock, patch

import pytest

from intention_graph.modular_code_gen.models import ModuleSpec
from intention_graph.modular_code_gen.module_decomposer import (
    ModuleDecomposer,
    _parse_json_array,
)


# ── Mock LLM response ───────────────────────────────────────────────────────

_MOCK_RESPONSE = json.dumps([
    {
        "module_id": "game_state",
        "description": "Manages game state, score, lives",
        "core_systems": ["score_system"],
        "dependencies": [],
    },
    {
        "module_id": "player",
        "description": "Player movement and input",
        "core_systems": ["player_control"],
        "dependencies": ["game_state"],
    },
    {
        "module_id": "shooting",
        "description": "Bullet spawning and collision",
        "core_systems": ["shooting_system", "collision_system"],
        "dependencies": ["game_state", "player"],
    },
    {
        "module_id": "enemy",
        "description": "Enemy spawning and AI",
        "core_systems": ["enemy_ai"],
        "dependencies": ["game_state"],
    },
])


def _mock_client():
    """Create a mock Anthropic client that returns _MOCK_RESPONSE."""
    client = MagicMock()
    response = MagicMock()
    response.content = [MagicMock(text=_MOCK_RESPONSE)]
    client.messages.create.return_value = response
    return client


# ── Tests ────────────────────────────────────────────────────────────────────


class TestParseJsonArray:
    def test_plain_array(self):
        result = _parse_json_array('[{"a": 1}]')
        assert result == [{"a": 1}]

    def test_fenced_code_block(self):
        result = _parse_json_array('```json\n[{"a": 1}]\n```')
        assert result == [{"a": 1}]

    def test_embedded_in_text(self):
        result = _parse_json_array('Here is the result:\n[{"a": 1}]\nDone.')
        assert result == [{"a": 1}]

    def test_invalid_returns_empty(self):
        assert _parse_json_array("not json") == []


class TestDecompose:
    @patch("intention_graph.modular_code_gen.module_decomposer.anthropic.Anthropic")
    def test_decompose_parses_response(self, mock_anthropic_cls):
        mock_anthropic_cls.return_value = _mock_client()
        decomposer = ModuleDecomposer(api_key="test-key")
        specs = decomposer.decompose(
            prd_document="Test PRD",
            wireframe={"interfaces": [{"interface_id": "gameplay"}]},
            core_systems=["score_system", "player_control", "shooting_system",
                          "collision_system", "enemy_ai"],
            complexity="arcade",
        )
        assert all(isinstance(s, ModuleSpec) for s in specs)
        assert len(specs) == 4

    @patch("intention_graph.modular_code_gen.module_decomposer.anthropic.Anthropic")
    def test_all_core_systems_covered(self, mock_anthropic_cls):
        mock_anthropic_cls.return_value = _mock_client()
        decomposer = ModuleDecomposer(api_key="test-key")
        core_systems = ["score_system", "player_control", "shooting_system",
                        "collision_system", "enemy_ai"]
        specs = decomposer.decompose(
            prd_document="Test PRD",
            wireframe={"interfaces": []},
            core_systems=core_systems,
        )
        covered = set()
        for s in specs:
            covered.update(s.core_systems)
        for cs in core_systems:
            assert cs in covered, f"core_system '{cs}' not covered"

    @patch("intention_graph.modular_code_gen.module_decomposer.anthropic.Anthropic")
    def test_module_count_within_bounds(self, mock_anthropic_cls):
        mock_anthropic_cls.return_value = _mock_client()
        decomposer = ModuleDecomposer(api_key="test-key")
        specs = decomposer.decompose(
            prd_document="Test PRD",
            wireframe={"interfaces": []},
            core_systems=["a", "b", "c"],
            complexity="arcade",
        )
        assert 3 <= len(specs) <= 7

    @patch("intention_graph.modular_code_gen.module_decomposer.anthropic.Anthropic")
    def test_acyclic_dependencies(self, mock_anthropic_cls):
        mock_anthropic_cls.return_value = _mock_client()
        decomposer = ModuleDecomposer(api_key="test-key")
        specs = decomposer.decompose(
            prd_document="Test PRD",
            wireframe={"interfaces": []},
            core_systems=["a"],
        )
        # Build adjacency and check for cycles via DFS
        adj = {s.module_id: s.dependencies for s in specs}
        visited = set()
        in_stack = set()

        def has_cycle(node):
            if node in in_stack:
                return True
            if node in visited:
                return False
            visited.add(node)
            in_stack.add(node)
            for dep in adj.get(node, []):
                if has_cycle(dep):
                    return True
            in_stack.discard(node)
            return False

        for mod_id in adj:
            assert not has_cycle(mod_id), f"Cycle detected involving {mod_id}"

    @patch("intention_graph.modular_code_gen.module_decomposer.anthropic.Anthropic")
    def test_game_state_module_present(self, mock_anthropic_cls):
        mock_anthropic_cls.return_value = _mock_client()
        decomposer = ModuleDecomposer(api_key="test-key")
        specs = decomposer.decompose(
            prd_document="Test PRD",
            wireframe={"interfaces": []},
            core_systems=["a"],
        )
        assert any(s.module_id == "game_state" for s in specs)

    @patch("intention_graph.modular_code_gen.module_decomposer.anthropic.Anthropic")
    def test_game_state_injected_if_missing(self, mock_anthropic_cls):
        """If LLM omits game_state, it gets injected."""
        no_gs_response = json.dumps([
            {"module_id": "player", "description": "Player", "core_systems": ["a"], "dependencies": []},
        ])
        client = MagicMock()
        response = MagicMock()
        response.content = [MagicMock(text=no_gs_response)]
        client.messages.create.return_value = response
        mock_anthropic_cls.return_value = client

        decomposer = ModuleDecomposer(api_key="test-key")
        specs = decomposer.decompose(
            prd_document="Test PRD",
            wireframe={"interfaces": []},
            core_systems=["a"],
        )
        assert specs[0].module_id == "game_state"
