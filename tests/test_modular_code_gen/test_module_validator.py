"""Tests for module validator."""

from intention_graph.modular_code_gen.models import (
    FunctionSig,
    ModuleCode,
    ModuleInterface,
    ParamDef,
)
from intention_graph.modular_code_gen.module_validator import validate_module


def _make_interface(exports=None):
    return ModuleInterface(
        module_id="shooting",
        description="Shooting system",
        exports=exports
        or [
            FunctionSig(name="init", params=[]),
            FunctionSig(name="update", params=[ParamDef(name="dt", type="number")]),
            FunctionSig(name="fire", params=[]),
        ],
        imports=["game_state"],
        state_access=["GameState"],
    )


_VALID_CODE = """\
const ShootingSystem = (function() {
    const bullets = [];
    function init() { bullets.length = 0; }
    function update(dt) {
        for (const b of bullets) { b.y -= b.speed * dt; }
    }
    function fire() { bullets.push({x: 0, y: 0, speed: 5}); }
    return { init, update, fire };
})();
"""


class TestValidModule:
    def test_valid_module_passes(self):
        code = ModuleCode(module_id="shooting", js_code=_VALID_CODE)
        result = validate_module(code, _make_interface())
        assert result.is_valid
        assert result.issues == []


class TestMissingExport:
    def test_missing_export_detected(self):
        code_without_fire = """\
const ShootingSystem = (function() {
    function init() {}
    function update(dt) {}
    return { init, update };
})();
"""
        code = ModuleCode(module_id="shooting", js_code=code_without_fire)
        result = validate_module(code, _make_interface())
        assert not result.is_valid
        assert any("fire" in issue for issue in result.issues)


class TestUnbalancedBraces:
    def test_unbalanced_braces_detected(self):
        bad_code = """\
const ShootingSystem = (function() {
    function init() {}
    function update(dt) {}
    function fire() {}
    return { init, update, fire };
"""  # Missing closing })();
        code = ModuleCode(module_id="shooting", js_code=bad_code)
        result = validate_module(code, _make_interface())
        assert not result.is_valid
        assert any("braces" in issue.lower() for issue in result.issues)


class TestEmptyCode:
    def test_empty_code_fails(self):
        code = ModuleCode(module_id="shooting", js_code="")
        result = validate_module(code, _make_interface())
        assert not result.is_valid
        assert any("short" in issue.lower() for issue in result.issues)

    def test_trivially_short_code_fails(self):
        code = ModuleCode(module_id="shooting", js_code="var x = 1;")
        result = validate_module(code, _make_interface())
        assert not result.is_valid
