"""Tests for assembly agent."""

import json
from unittest.mock import MagicMock, patch

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
from intention_graph.modular_code_gen.assembly_agent import (
    AssemblyAgent,
    _parse_code_response,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_arch():
    return ArchitectureDoc(
        game_title="Test Game",
        modules=[
            ModuleInterface(
                module_id="game_state",
                description="State",
                exports=[FunctionSig(name="init", params=[])],
                imports=[],
                state_access=["GameState"],
            ),
        ],
        shared_data=[
            SharedDataStructure(
                name="GameState",
                fields=[FieldDef(name="score", type="number")],
            )
        ],
        events=[],
        init_order=["game_state"],
        update_order=[],
        render_order=[],
    )


_MOCK_LLM_OUTPUT = """\
Here are the assembled files:

```index.html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Test Game</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div id="start_screen" class="screen">
        <h1>Test Game</h1>
        <button onclick="showScreen('gameplay')">Play</button>
    </div>
    <div id="gameplay" class="screen" style="display:none">
        <canvas id="game_canvas"></canvas>
    </div>
    <script src="core.js"></script>
</body>
</html>
```

```style.css
body { margin: 0; background: #000; }
.screen { display: none; width: 100vw; height: 100vh; }
#start_screen { display: block; }
canvas { width: 100%; height: 100%; }
```

```core.js
const EventBus = {
    _handlers: {},
    on(e, fn) { (this._handlers[e] = this._handlers[e] || []).push(fn); },
    emit(e, data) { (this._handlers[e] || []).forEach(fn => fn(data)); }
};

const GameState = { score: 0 };

function showScreen(id) {
    document.querySelectorAll('.screen').forEach(s => s.style.display = 'none');
    document.getElementById(id).style.display = 'block';
}

// Module: game_state
const GameStateModule = (function() {
    function init() { GameState.score = 0; }
    return { init };
})();

GameStateModule.init();
```
"""


def _mock_client():
    client = MagicMock()
    stream_ctx = MagicMock()
    stream_ctx.__enter__ = MagicMock(return_value=stream_ctx)
    stream_ctx.__exit__ = MagicMock(return_value=False)
    stream_ctx.text_stream = iter([_MOCK_LLM_OUTPUT])
    client.messages.stream.return_value = stream_ctx
    return client


# ── Tests ────────────────────────────────────────────────────────────────────


class TestParseCodeResponse:
    def test_extracts_three_files(self):
        result = _parse_code_response(_MOCK_LLM_OUTPUT)
        assert "index.html" in result
        assert "style.css" in result
        assert "core.js" in result
        assert "<!DOCTYPE html>" in result["index.html"]
        assert "body" in result["style.css"]
        assert "EventBus" in result["core.js"]

    def test_empty_input(self):
        result = _parse_code_response("")
        assert result["index.html"] == ""
        assert result["style.css"] == ""
        assert result["core.js"] == ""


class TestAssemble:
    @patch("intention_graph.modular_code_gen.assembly_agent.anthropic.Anthropic")
    def test_assemble_mocked(self, mock_cls):
        mock_cls.return_value = _mock_client()
        agent = AssemblyAgent(api_key="test-key")
        modules = [
            ModuleCode(
                module_id="game_state",
                js_code='const GS = (function() { function init(){} return {init}; })();',
            )
        ]
        result = agent.assemble(
            modules=modules,
            architecture=_make_arch(),
            wireframe={"interfaces": [{"interface_id": "start_screen"}]},
            prd_document="Test PRD",
        )
        assert "index.html" in result
        assert "style.css" in result
        assert "core.js" in result
        assert len(result["index.html"]) > 0

    @patch("intention_graph.modular_code_gen.assembly_agent.anthropic.Anthropic")
    def test_reuses_parse_code_response(self, mock_cls):
        """Verify the parse function correctly extracts from mock LLM output."""
        mock_cls.return_value = _mock_client()
        agent = AssemblyAgent(api_key="test-key")
        modules = [ModuleCode(module_id="game_state", js_code="var x=1;")]
        result = agent.assemble(modules, _make_arch(), {"interfaces": []}, "PRD")
        # All 3 keys should be present and non-empty
        assert all(result[k] for k in ("index.html", "style.css", "core.js"))
