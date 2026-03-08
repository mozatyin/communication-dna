"""Tests for architecture designer."""

import json
from unittest.mock import MagicMock, patch

import pytest

from intention_graph.modular_code_gen.models import (
    ArchitectureDoc,
    ModuleSpec,
)
from intention_graph.modular_code_gen.architecture_designer import (
    ArchitectureDesigner,
    _parse_architecture,
    _parse_json,
)


# ── Mock LLM response ───────────────────────────────────────────────────────

_MOCK_ARCH = {
    "game_title": "Space Shooter",
    "modules": [
        {
            "module_id": "game_state",
            "description": "Shared state management",
            "exports": [
                {"name": "init", "params": [], "returns": "void", "description": "Initialize state"},
                {"name": "getState", "params": [], "returns": "object", "description": "Get state"},
            ],
            "imports": [],
            "state_access": ["GameState"],
            "update_function": None,
            "render_function": None,
        },
        {
            "module_id": "player",
            "description": "Player movement",
            "exports": [
                {"name": "init", "params": [], "returns": "void"},
                {"name": "update", "params": [{"name": "dt", "type": "number"}], "returns": "void"},
                {"name": "render", "params": [{"name": "ctx", "type": "CanvasRenderingContext2D"}], "returns": "void"},
            ],
            "imports": ["game_state"],
            "state_access": ["GameState", "PlayerState"],
            "update_function": "update",
            "render_function": "render",
        },
        {
            "module_id": "shooting",
            "description": "Bullet system",
            "exports": [
                {"name": "init", "params": [], "returns": "void"},
                {"name": "update", "params": [{"name": "dt", "type": "number"}], "returns": "void"},
                {"name": "render", "params": [{"name": "ctx", "type": "CanvasRenderingContext2D"}], "returns": "void"},
                {"name": "fire", "params": [], "returns": "void"},
            ],
            "imports": ["game_state", "player"],
            "state_access": ["GameState"],
            "update_function": "update",
            "render_function": "render",
        },
    ],
    "shared_data": [
        {
            "name": "GameState",
            "fields": [
                {"name": "score", "type": "number", "default": "0"},
                {"name": "lives", "type": "number", "default": "3"},
                {"name": "gameStatus", "type": "string", "default": "menu"},
            ],
            "description": "Main game state",
        },
        {
            "name": "PlayerState",
            "fields": [
                {"name": "x", "type": "number", "default": "540"},
                {"name": "y", "type": "number", "default": "1600"},
            ],
            "description": "Player position",
        },
    ],
    "events": [
        {
            "name": "ENEMY_DESTROYED",
            "payload": {"enemyId": "string", "points": "number"},
            "producers": ["shooting"],
            "consumers": ["game_state"],
        },
    ],
    "init_order": ["game_state", "player", "shooting"],
    "update_order": ["player", "shooting"],
    "render_order": ["player", "shooting"],
    "global_constants": {"CANVAS_WIDTH": "1080", "CANVAS_HEIGHT": "1920"},
}


def _mock_client(response_data=None):
    client = MagicMock()
    response = MagicMock()
    response.content = [MagicMock(text=json.dumps(response_data or _MOCK_ARCH))]
    client.messages.create.return_value = response
    return client


_INPUT_SPECS = [
    ModuleSpec(module_id="game_state", description="State", core_systems=["score"], dependencies=[]),
    ModuleSpec(module_id="player", description="Player", core_systems=["control"], dependencies=["game_state"]),
    ModuleSpec(module_id="shooting", description="Shooting", core_systems=["bullets"], dependencies=["game_state"]),
]


# ── Tests ────────────────────────────────────────────────────────────────────


class TestParseJson:
    def test_plain_json(self):
        assert _parse_json('{"a": 1}') == {"a": 1}

    def test_fenced_json(self):
        assert _parse_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_embedded_json(self):
        assert _parse_json('Here:\n{"a": 1}\nDone') == {"a": 1}

    def test_invalid_returns_empty(self):
        assert _parse_json("not json") == {}


class TestParseArchitecture:
    def test_parses_mock_data(self):
        arch = _parse_architecture(_MOCK_ARCH)
        assert isinstance(arch, ArchitectureDoc)
        assert arch.game_title == "Space Shooter"
        assert len(arch.modules) == 3
        assert len(arch.shared_data) == 2
        assert len(arch.events) == 1


class TestDesign:
    @patch("intention_graph.modular_code_gen.architecture_designer.anthropic.Anthropic")
    def test_design_parses_response(self, mock_cls):
        mock_cls.return_value = _mock_client()
        designer = ArchitectureDesigner(api_key="test-key")
        arch = designer.design(
            prd_document="Test PRD",
            wireframe={"interfaces": [{"interface_id": "gameplay"}]},
            modules=_INPUT_SPECS,
        )
        assert isinstance(arch, ArchitectureDoc)
        assert arch.game_title == "Space Shooter"

    @patch("intention_graph.modular_code_gen.architecture_designer.anthropic.Anthropic")
    def test_all_module_ids_present(self, mock_cls):
        mock_cls.return_value = _mock_client()
        designer = ArchitectureDesigner(api_key="test-key")
        arch = designer.design("PRD", {"interfaces": []}, _INPUT_SPECS)
        arch_ids = {m.module_id for m in arch.modules}
        for spec in _INPUT_SPECS:
            assert spec.module_id in arch_ids

    @patch("intention_graph.modular_code_gen.architecture_designer.anthropic.Anthropic")
    def test_init_order_valid(self, mock_cls):
        mock_cls.return_value = _mock_client()
        designer = ArchitectureDesigner(api_key="test-key")
        arch = designer.design("PRD", {"interfaces": []}, _INPUT_SPECS)
        arch_ids = {m.module_id for m in arch.modules}
        for mid in arch.init_order:
            assert mid in arch_ids

    @patch("intention_graph.modular_code_gen.architecture_designer.anthropic.Anthropic")
    def test_event_refs_valid(self, mock_cls):
        mock_cls.return_value = _mock_client()
        designer = ArchitectureDesigner(api_key="test-key")
        arch = designer.design("PRD", {"interfaces": []}, _INPUT_SPECS)
        arch_ids = {m.module_id for m in arch.modules}
        for event in arch.events:
            for mid in event.producers + event.consumers:
                assert mid in arch_ids, f"Event {event.name} refs unknown module {mid}"

    @patch("intention_graph.modular_code_gen.architecture_designer.anthropic.Anthropic")
    def test_every_module_has_exports(self, mock_cls):
        mock_cls.return_value = _mock_client()
        designer = ArchitectureDesigner(api_key="test-key")
        arch = designer.design("PRD", {"interfaces": []}, _INPUT_SPECS)
        for m in arch.modules:
            assert len(m.exports) > 0, f"Module {m.module_id} has no exports"

    @patch("intention_graph.modular_code_gen.architecture_designer.anthropic.Anthropic")
    def test_missing_module_raises(self, mock_cls):
        """If LLM output is missing a module that was in input, raise."""
        incomplete = dict(_MOCK_ARCH)
        incomplete["modules"] = [_MOCK_ARCH["modules"][0]]  # Only game_state
        incomplete["init_order"] = ["game_state"]
        incomplete["update_order"] = []
        incomplete["render_order"] = []
        mock_cls.return_value = _mock_client(incomplete)
        designer = ArchitectureDesigner(api_key="test-key")
        with pytest.raises(ValueError, match="missing modules"):
            designer.design("PRD", {"interfaces": []}, _INPUT_SPECS)
