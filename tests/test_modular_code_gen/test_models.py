"""Tests for modular code generation Pydantic models."""

import json

import pytest
from pydantic import ValidationError

from intention_graph.modular_code_gen.models import (
    ArchitectureDoc,
    AssembledCode,
    EventDef,
    FieldDef,
    FunctionSig,
    ModuleCode,
    ModuleInterface,
    ModuleSpec,
    ParamDef,
    SharedDataStructure,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_module_interface(module_id: str = "game_state") -> ModuleInterface:
    return ModuleInterface(
        module_id=module_id,
        description="Manages shared game state",
        exports=[FunctionSig(name="init", params=[])],
        imports=[],
        state_access=["GameState"],
    )


def _make_arch_doc(**overrides) -> ArchitectureDoc:
    defaults = dict(
        game_title="Test Game",
        modules=[_make_module_interface("game_state"), _make_module_interface("player")],
        shared_data=[
            SharedDataStructure(
                name="GameState",
                fields=[FieldDef(name="score", type="number", default="0")],
            )
        ],
        events=[
            EventDef(
                name="SCORE_CHANGED",
                payload={"score": "number"},
                producers=["game_state"],
                consumers=["player"],
            )
        ],
        init_order=["game_state", "player"],
        update_order=["player"],
        render_order=["player"],
    )
    defaults.update(overrides)
    return ArchitectureDoc(**defaults)


# ── Minimal construction ─────────────────────────────────────────────────────


class TestMinimalConstruction:
    def test_field_def(self):
        f = FieldDef(name="score", type="number")
        assert f.name == "score"
        assert f.default == ""

    def test_shared_data_structure(self):
        s = SharedDataStructure(name="GameState", fields=[])
        assert s.name == "GameState"

    def test_event_def(self):
        e = EventDef(name="HIT", payload={"x": "number"}, producers=["a"], consumers=["b"])
        assert e.name == "HIT"

    def test_param_def(self):
        p = ParamDef(name="dt", type="number")
        assert p.name == "dt"

    def test_function_sig(self):
        f = FunctionSig(name="update", params=[ParamDef(name="dt", type="number")])
        assert f.returns == "void"

    def test_module_spec(self):
        m = ModuleSpec(
            module_id="shooting",
            description="Handles bullets",
            core_systems=["shooting_system"],
            dependencies=["game_state"],
        )
        assert m.module_id == "shooting"

    def test_module_interface(self):
        m = _make_module_interface()
        assert m.module_id == "game_state"
        assert len(m.exports) == 1

    def test_architecture_doc(self):
        doc = _make_arch_doc()
        assert doc.game_title == "Test Game"
        assert len(doc.modules) == 2

    def test_module_code(self):
        mc = ModuleCode(module_id="shooting", js_code="const x = 1;")
        assert not mc.is_stub

    def test_assembled_code(self):
        ac = AssembledCode(html="<html></html>", css="body{}", js="var x=1;")
        assert ac.html.startswith("<html")


# ── JSON round-trip ──────────────────────────────────────────────────────────


class TestJsonRoundTrip:
    def test_module_spec_roundtrip(self):
        original = ModuleSpec(
            module_id="enemy",
            description="Enemy spawning and AI",
            core_systems=["enemy_ai", "spawning"],
            dependencies=["game_state"],
        )
        data = json.loads(original.model_dump_json())
        restored = ModuleSpec(**data)
        assert restored == original

    def test_architecture_doc_roundtrip(self):
        original = _make_arch_doc()
        data = json.loads(original.model_dump_json())
        restored = ArchitectureDoc(**data)
        assert restored.game_title == original.game_title
        assert len(restored.modules) == len(original.modules)
        assert restored.init_order == original.init_order

    def test_module_code_roundtrip(self):
        original = ModuleCode(module_id="ui", js_code="function render(){}", is_stub=True)
        data = json.loads(original.model_dump_json())
        restored = ModuleCode(**data)
        assert restored == original


# ── ArchitectureDoc validation ───────────────────────────────────────────────


class TestArchitectureDocValidation:
    def test_valid_init_order(self):
        doc = _make_arch_doc()
        assert doc.init_order == ["game_state", "player"]

    def test_invalid_init_order_raises(self):
        with pytest.raises(ValidationError, match="init_order references unknown module"):
            _make_arch_doc(init_order=["game_state", "nonexistent"])

    def test_invalid_update_order_raises(self):
        with pytest.raises(ValidationError, match="update_order references unknown module"):
            _make_arch_doc(update_order=["nonexistent"])

    def test_invalid_render_order_raises(self):
        with pytest.raises(ValidationError, match="render_order references unknown module"):
            _make_arch_doc(render_order=["nonexistent"])

    def test_empty_orders_valid(self):
        doc = _make_arch_doc(update_order=[], render_order=[])
        assert doc.update_order == []
