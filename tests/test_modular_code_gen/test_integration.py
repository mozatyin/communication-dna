"""Integration tests for modular code generation pipeline."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from intention_graph.modular_code_gen.models import (
    ArchitectureDoc,
    EventDef,
    FieldDef,
    FunctionSig,
    ModuleCode,
    ModuleInterface,
    ModuleSpec,
    ParamDef,
    SharedDataStructure,
)


# ── Test data ────────────────────────────────────────────────────────────────

_PRD = """\
## Game Overview
Space Shooter — a vertical scrolling shooter where the player controls a \
spaceship, shoots enemies, and collects power-ups.

## Core Game Loop
The player moves left/right, fires bullets at waves of enemies descending \
from the top. Score increases for each enemy destroyed.

## Game Systems
### Shooting System
Player fires bullets upward. Bullets destroy enemies on collision.
### Enemy System
Enemies spawn in waves from the top and move downward.
### Score System
Points awarded per enemy destroyed. High score tracked.
"""

_WIREFRAME = {
    "project": {"title": "Space Shooter", "global_resolution": {"width": 1080, "height": 1920}},
    "interfaces": [
        {
            "interface_id": "start_screen",
            "interface_name": "Start",
            "type": "page",
            "parents": [],
            "children": ["gameplay"],
            "elements": [
                {"id": "bg", "type": "image", "style": {}, "event": None},
                {"id": "btn_play", "type": "button", "inner_text": "Play",
                 "style": {"background-color": "#E8A43A"},
                 "event": "click", "target_interface_id": "gameplay"},
            ],
        },
        {
            "interface_id": "gameplay",
            "interface_name": "Gameplay",
            "type": "page",
            "parents": ["start_screen"],
            "children": ["game_over"],
            "elements": [
                {"id": "canvas", "type": "css", "style": {}, "event": None},
                {"id": "score_text", "type": "text", "style": {}, "event": None},
            ],
        },
        {
            "interface_id": "game_over",
            "interface_name": "Game Over",
            "type": "page",
            "parents": ["gameplay"],
            "children": ["start_screen", "gameplay"],
            "elements": [
                {"id": "final_score", "type": "text", "style": {}, "event": None},
                {"id": "btn_retry", "type": "button", "inner_text": "Retry",
                 "style": {}, "event": "click", "target_interface_id": "gameplay"},
            ],
        },
    ],
}

_CORE_SYSTEMS = ["shooting_system", "enemy_system", "score_system"]

# ── Mock responses for each stage ────────────────────────────────────────────

_MOCK_DECOMPOSE = [
    {"module_id": "game_state", "description": "State", "core_systems": ["score_system"], "dependencies": []},
    {"module_id": "player", "description": "Player ship", "core_systems": [], "dependencies": ["game_state"]},
    {"module_id": "shooting", "description": "Bullets", "core_systems": ["shooting_system"], "dependencies": ["game_state", "player"]},
    {"module_id": "enemy", "description": "Enemies", "core_systems": ["enemy_system"], "dependencies": ["game_state"]},
]

_MOCK_ARCH = {
    "game_title": "Space Shooter",
    "modules": [
        {"module_id": "game_state", "description": "State",
         "exports": [{"name": "init", "params": [], "returns": "void"}],
         "imports": [], "state_access": ["GameState"],
         "update_function": None, "render_function": None},
        {"module_id": "player", "description": "Player",
         "exports": [
             {"name": "init", "params": [], "returns": "void"},
             {"name": "update", "params": [{"name": "dt", "type": "number"}], "returns": "void"},
             {"name": "render", "params": [{"name": "ctx", "type": "CanvasRenderingContext2D"}], "returns": "void"},
         ],
         "imports": ["game_state"], "state_access": ["GameState"],
         "update_function": "update", "render_function": "render"},
        {"module_id": "shooting", "description": "Bullets",
         "exports": [
             {"name": "init", "params": [], "returns": "void"},
             {"name": "update", "params": [{"name": "dt", "type": "number"}], "returns": "void"},
             {"name": "render", "params": [{"name": "ctx", "type": "CanvasRenderingContext2D"}], "returns": "void"},
         ],
         "imports": ["game_state", "player"], "state_access": ["GameState"],
         "update_function": "update", "render_function": "render"},
        {"module_id": "enemy", "description": "Enemies",
         "exports": [
             {"name": "init", "params": [], "returns": "void"},
             {"name": "update", "params": [{"name": "dt", "type": "number"}], "returns": "void"},
             {"name": "render", "params": [{"name": "ctx", "type": "CanvasRenderingContext2D"}], "returns": "void"},
         ],
         "imports": ["game_state"], "state_access": ["GameState"],
         "update_function": "update", "render_function": "render"},
    ],
    "shared_data": [
        {"name": "GameState", "fields": [
            {"name": "score", "type": "number", "default": "0"},
            {"name": "lives", "type": "number", "default": "3"},
            {"name": "gameStatus", "type": "string", "default": "menu"},
        ], "description": "Core game state"},
    ],
    "events": [
        {"name": "ENEMY_DESTROYED", "payload": {"points": "number"},
         "producers": ["shooting"], "consumers": ["game_state"]},
    ],
    "init_order": ["game_state", "player", "shooting", "enemy"],
    "update_order": ["player", "shooting", "enemy"],
    "render_order": ["player", "shooting", "enemy"],
    "global_constants": {"CANVAS_WIDTH": "1080", "CANVAS_HEIGHT": "1920"},
}

_MOCK_MODULE_CODE = """\
const {camel} = (function() {{
    function init() {{}}
    function update(dt) {{}}
    function render(ctx) {{}}
    return {{ init, update, render }};
}})();
"""

_MOCK_ASSEMBLY = """\
```index.html
<!DOCTYPE html>
<html><head><title>Space Shooter</title><link rel="stylesheet" href="style.css"></head>
<body>
<div id="start_screen" class="screen"><button onclick="showScreen('gameplay')">Play</button></div>
<div id="gameplay" class="screen" style="display:none"><canvas id="game_canvas"></canvas></div>
<div id="game_over" class="screen" style="display:none"><button onclick="showScreen('gameplay')">Retry</button></div>
<script src="core.js"></script></body></html>
```

```style.css
body { margin: 0; background: #000; }
.screen { display: none; width: 100vw; height: 100vh; }
#start_screen { display: block; }
```

```core.js
const EventBus = { _h: {}, on(e,f){(this._h[e]=this._h[e]||[]).push(f);}, emit(e,d){(this._h[e]||[]).forEach(f=>f(d));} };
const GameState = { score: 0, lives: 3, gameStatus: 'menu' };
function showScreen(id) { document.querySelectorAll('.screen').forEach(s=>s.style.display='none'); document.getElementById(id).style.display='block'; }
const GameStateModule = (function() { function init(){} return {init}; })();
const Player = (function() { function init(){} function update(dt){} function render(ctx){} return {init,update,render}; })();
const Shooting = (function() { function init(){} function update(dt){} function render(ctx){} return {init,update,render}; })();
const Enemy = (function() { function init(){} function update(dt){} function render(ctx){} return {init,update,render}; })();
GameStateModule.init(); Player.init(); Shooting.init(); Enemy.init();
```
"""


# ── Full pipeline mock test ──────────────────────────────────────────────────


def test_full_pipeline_mocked():
    """All 4 stages with mocked LLM responses."""
    from intention_graph.game_code_generator import GameCodeGenerator

    with patch("intention_graph.game_code_generator.anthropic.Anthropic"):
        gen = GameCodeGenerator(api_key="test-key")

    # Mock Stage A: Decomposer
    with (
        patch("intention_graph.game_code_generator.ModuleDecomposer") as mock_decomp,
        patch("intention_graph.game_code_generator.ArchitectureDesigner") as mock_arch_cls,
        patch("intention_graph.game_code_generator.ModuleGenerator") as mock_gen_cls,
        patch("intention_graph.game_code_generator.AssemblyAgent") as mock_asm_cls,
    ):
        # Stage A
        mock_decomp.return_value.decompose.return_value = [
            ModuleSpec(**d) for d in _MOCK_DECOMPOSE
        ]

        # Stage B
        from intention_graph.modular_code_gen.architecture_designer import _parse_architecture
        mock_arch_cls.return_value.design.return_value = _parse_architecture(_MOCK_ARCH)

        # Stage C
        mock_gen_cls.return_value.generate_all_parallel.return_value = [
            ModuleCode(
                module_id=m["module_id"],
                js_code=_MOCK_MODULE_CODE.format(camel=m["module_id"].title().replace("_", "")),
            )
            for m in _MOCK_DECOMPOSE
        ]

        # Stage D
        from intention_graph.modular_code_gen.assembly_agent import _parse_code_response
        mock_asm_cls.return_value.assemble.return_value = _parse_code_response(_MOCK_ASSEMBLY)

        # Run
        result = gen.modular_generate(
            prd_document=_PRD,
            wireframe=_WIREFRAME,
            core_systems=_CORE_SYSTEMS,
            complexity="arcade",
        )

    # Verify
    assert "index.html" in result
    assert "style.css" in result
    assert "core.js" in result
    assert "<!DOCTYPE html>" in result["index.html"]
    assert "showScreen" in result["core.js"]

    # Verify all stages were called
    mock_decomp.return_value.decompose.assert_called_once()
    mock_arch_cls.return_value.design.assert_called_once()
    mock_gen_cls.return_value.generate_all_parallel.assert_called_once()
    mock_asm_cls.return_value.assemble.assert_called_once()


# ── Real API integration test ────────────────────────────────────────────────


@pytest.mark.slow
def test_modular_vs_single_shot():
    """Real API: compare modular vs single-shot on space_shooter."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")

    from intention_graph.game_code_generator import GameCodeGenerator
    from intention_graph.game_code_quality import evaluate

    gen = GameCodeGenerator(api_key=api_key)

    # Single-shot
    single = gen.generate(_PRD, _WIREFRAME)
    single_report = evaluate(
        single.get("index.html", ""),
        single.get("style.css", ""),
        single.get("core.js", ""),
        _WIREFRAME,
    )
    print(f"Single-shot: {single_report.overall_score:.0%}")

    # Modular
    modular = gen.modular_generate(
        _PRD, _WIREFRAME,
        core_systems=_CORE_SYSTEMS,
        complexity="arcade",
    )
    modular_report = evaluate(
        modular.get("index.html", ""),
        modular.get("style.css", ""),
        modular.get("core.js", ""),
        _WIREFRAME,
    )
    print(f"Modular: {modular_report.overall_score:.0%}")

    # Both should produce valid output
    assert len(single.get("core.js", "")) > 100
    assert len(modular.get("core.js", "")) > 100
