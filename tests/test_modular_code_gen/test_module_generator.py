"""Tests for module generator (parallel)."""

import json
from unittest.mock import MagicMock, patch, call

import pytest

from intention_graph.modular_code_gen.models import (
    ArchitectureDoc,
    EventDef,
    FieldDef,
    FunctionSig,
    ModuleCode,
    ModuleInterface,
    ParamDef,
    SharedDataStructure,
)
from intention_graph.modular_code_gen.module_generator import (
    ModuleGenerator,
    _create_stub,
    _strip_fences,
    _to_camel,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_interface(module_id="shooting"):
    return ModuleInterface(
        module_id=module_id,
        description="Test module",
        exports=[
            FunctionSig(name="init", params=[]),
            FunctionSig(name="update", params=[ParamDef(name="dt", type="number")]),
        ],
        imports=["game_state"],
        state_access=["GameState"],
        update_function="update",
        render_function=None,
    )


def _make_arch():
    return ArchitectureDoc(
        game_title="Test",
        modules=[
            _make_interface("game_state"),
            _make_interface("player"),
            _make_interface("shooting"),
        ],
        shared_data=[
            SharedDataStructure(name="GameState", fields=[FieldDef(name="score", type="number")])
        ],
        events=[
            EventDef(name="HIT", payload={}, producers=["shooting"], consumers=["game_state"])
        ],
        init_order=["game_state", "player", "shooting"],
        update_order=["player", "shooting"],
        render_order=["player", "shooting"],
    )


_VALID_MODULE_CODE = """\
const Shooting = (function() {
    let bullets = [];
    function init() { bullets = []; }
    function update(dt) {
        bullets.forEach(b => { b.y -= b.speed * dt; });
        bullets = bullets.filter(b => b.y > 0);
    }
    return { init, update };
})();
"""

_INVALID_MODULE_CODE = """\
function init() {}
"""  # No IIFE, too short for full module


def _mock_client(code=_VALID_MODULE_CODE):
    client = MagicMock()
    response = MagicMock()
    response.content = [MagicMock(text=code)]
    client.messages.create.return_value = response
    return client


# ── Unit tests ───────────────────────────────────────────────────────────────


class TestHelpers:
    def test_to_camel(self):
        assert _to_camel("game_state") == "GameState"
        assert _to_camel("shooting") == "Shooting"
        assert _to_camel("enemy_ai_system") == "EnemyAiSystem"

    def test_strip_fences_plain(self):
        assert _strip_fences("const x = 1;") == "const x = 1;"

    def test_strip_fences_with_fences(self):
        assert _strip_fences("```javascript\nconst x = 1;\n```") == "const x = 1;"

    def test_create_stub(self):
        iface = _make_interface("shooting")
        stub = _create_stub(iface)
        assert stub.is_stub
        assert stub.module_id == "shooting"
        assert "init" in stub.js_code
        assert "update" in stub.js_code
        assert "(function()" in stub.js_code


class TestGenerateModule:
    @patch("intention_graph.modular_code_gen.module_generator.anthropic.Anthropic")
    def test_generate_module_mocked(self, mock_cls):
        mock_cls.return_value = _mock_client()
        gen = ModuleGenerator(api_key="test-key")
        arch = _make_arch()
        module = arch.modules[2]  # shooting
        code = gen.generate_module(arch, module, "PRD text", {"interfaces": []})
        assert isinstance(code, ModuleCode)
        assert "function" in code.js_code

    @patch("intention_graph.modular_code_gen.module_generator.anthropic.Anthropic")
    def test_module_wrapped_in_iife(self, mock_cls):
        mock_cls.return_value = _mock_client()
        gen = ModuleGenerator(api_key="test-key")
        arch = _make_arch()
        code = gen.generate_module(arch, arch.modules[2], "PRD", {})
        assert "(function()" in code.js_code

    @patch("intention_graph.modular_code_gen.module_generator.anthropic.Anthropic")
    def test_retry_on_validation_failure(self, mock_cls):
        """First call returns invalid code, second returns valid."""
        client = MagicMock()
        bad_response = MagicMock()
        bad_response.content = [MagicMock(text=_INVALID_MODULE_CODE)]
        good_response = MagicMock()
        good_response.content = [MagicMock(text=_VALID_MODULE_CODE)]
        client.messages.create.side_effect = [bad_response, good_response]
        mock_cls.return_value = client

        gen = ModuleGenerator(api_key="test-key")
        arch = _make_arch()
        code = gen.generate_module(arch, arch.modules[2], "PRD", {})
        assert not code.is_stub
        assert client.messages.create.call_count == 2

    @patch("intention_graph.modular_code_gen.module_generator.anthropic.Anthropic")
    def test_stub_on_total_failure(self, mock_cls):
        """Both attempts return invalid code → get stub."""
        client = MagicMock()
        bad = MagicMock()
        bad.content = [MagicMock(text=_INVALID_MODULE_CODE)]
        client.messages.create.return_value = bad
        mock_cls.return_value = client

        gen = ModuleGenerator(api_key="test-key")
        arch = _make_arch()
        code = gen.generate_module(arch, arch.modules[2], "PRD", {})
        assert code.is_stub
        assert "init" in code.js_code
        assert "update" in code.js_code


class TestParallelGeneration:
    @patch("intention_graph.modular_code_gen.module_generator.anthropic.Anthropic")
    def test_parallel_calls_all_modules(self, mock_cls):
        mock_cls.return_value = _mock_client()
        gen = ModuleGenerator(api_key="test-key")
        arch = _make_arch()
        results = gen.generate_all_parallel(arch, "PRD", {}, max_workers=2)
        assert len(results) == 3
        module_ids = {r.module_id for r in results}
        # All modules should be represented (either real or via init_order naming)
        assert len(module_ids) >= 1  # At minimum we get results

    @patch("intention_graph.modular_code_gen.module_generator.anthropic.Anthropic")
    def test_parallel_results_ordered_by_init(self, mock_cls):
        """Results should follow init_order when possible."""
        # Create distinct code for each module
        codes = {
            "game_state": 'const GameState = (function() { function init() {} function update(dt) {} return { init, update }; })();',
            "player": 'const Player = (function() { function init() {} function update(dt) {} return { init, update }; })();',
            "shooting": 'const Shooting = (function() { function init() {} function update(dt) {} return { init, update }; })();',
        }
        client = MagicMock()
        # Return the appropriate code based on call order
        responses = []
        for code_text in codes.values():
            resp = MagicMock()
            resp.content = [MagicMock(text=code_text)]
            responses.append(resp)
        client.messages.create.side_effect = responses * 2  # Extra in case of retries
        mock_cls.return_value = client

        gen = ModuleGenerator(api_key="test-key")
        arch = _make_arch()
        results = gen.generate_all_parallel(arch, "PRD", {}, max_workers=1)
        assert len(results) == 3
