"""Tests for GameCodeGenerator (Stage 4)."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from intention_graph.game_code_generator import GameCodeGenerator, _parse_code_response


def _mock_stream(text: str) -> MagicMock:
    """Create a mock for the streaming context manager."""
    stream_mock = MagicMock()
    stream_mock.__enter__ = MagicMock(return_value=stream_mock)
    stream_mock.__exit__ = MagicMock(return_value=False)
    stream_mock.text_stream = iter([text])
    return stream_mock


_SAMPLE_CODE_RESPONSE = """\
Here are the 3 game files:

```index.html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Flappy Bird</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div id="start_screen" class="screen">
        <h1>Flappy Bird</h1>
        <button onclick="showScreen('gameplay')">Play</button>
    </div>
    <div id="gameplay" class="screen" style="display:none">
        <canvas id="game_canvas"></canvas>
        <div id="score">0</div>
    </div>
    <div id="game_over" class="screen" style="display:none">
        <h2>Game Over</h2>
        <button onclick="showScreen('gameplay')">Retry</button>
        <button onclick="showScreen('start_screen')">Menu</button>
    </div>
    <script src="core.js"></script>
</body>
</html>
```

```style.css
* { margin: 0; padding: 0; }
body { background: #4EC0CA; }
.screen { width: 100vw; height: 100vh; display: none; }
#start_screen { display: block; background: #4EC0CA; }
button { background: #E8A43A; color: white; padding: 15px 30px; border: none; }
#game_over { text-align: center; }
```

```core.js
const screens = document.querySelectorAll('.screen');

function showScreen(id) {
    screens.forEach(s => s.style.display = 'none');
    document.getElementById(id).style.display = 'block';
}

const canvas = document.getElementById('game_canvas');
const ctx = canvas.getContext('2d');
let gameRunning = false;
let score = 0;

function startGame() {
    score = 0;
    gameRunning = true;
    showScreen('gameplay');
    requestAnimationFrame(gameLoop);
}

function gameLoop() {
    if (!gameRunning) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    requestAnimationFrame(gameLoop);
}

function gameOver() {
    gameRunning = false;
    showScreen('game_over');
}

document.addEventListener('keydown', function(e) {
    if (e.code === 'Space') {
        // flap
    }
});
```
"""

_SAMPLE_PRD = "## Game Overview\nA Flappy Bird clone. Tap to fly through pipes."

_SAMPLE_WIREFRAME = {
    "project": {"title": "Flappy Bird", "global_resolution": {"width": 1080, "height": 1920}},
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
            "interface_name": "Game",
            "type": "page",
            "parents": ["start_screen"],
            "children": ["game_over"],
            "elements": [
                {"id": "bg", "type": "image", "style": {}, "event": None},
                {"id": "bird", "type": "image", "style": {}, "event": None},
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
                {"id": "bg", "type": "image", "style": {}, "event": None},
                {"id": "btn_retry", "type": "button", "inner_text": "Retry",
                 "style": {}, "event": "click", "target_interface_id": "gameplay"},
                {"id": "btn_menu", "type": "button", "inner_text": "Menu",
                 "style": {}, "event": "click", "target_interface_id": "start_screen"},
            ],
        },
    ],
}


# ── Constructor ──────────────────────────────────────────────────────────────


def test_generator_construction():
    with patch("intention_graph.game_code_generator.anthropic.Anthropic"):
        gen = GameCodeGenerator(api_key="test-key")
    assert gen._model == "claude-sonnet-4-20250514"


def test_generator_custom_model():
    with patch("intention_graph.game_code_generator.anthropic.Anthropic"):
        gen = GameCodeGenerator(api_key="test-key", model="custom-model")
    assert gen._model == "custom-model"


def test_generator_openrouter():
    with patch("intention_graph.game_code_generator.anthropic.Anthropic") as mock_cls:
        GameCodeGenerator(api_key="sk-or-test-key")
    call_kwargs = mock_cls.call_args.kwargs
    assert call_kwargs["base_url"] == "https://openrouter.ai/api"


# ── Response Parser ─────────────────────────────────────────────────────────


def test_parse_code_response_labeled_blocks():
    result = _parse_code_response(_SAMPLE_CODE_RESPONSE)
    assert "<!DOCTYPE html>" in result["index.html"]
    assert ".screen" in result["style.css"]
    assert "showScreen" in result["core.js"]


def test_parse_code_response_unlabeled_blocks():
    raw = (
        "```\n<!DOCTYPE html><html><head></head><body></body></html>\n```\n\n"
        "```\n* { margin: 0; }\nbody { color: red; }\n```\n\n"
        "```\nfunction main() { console.log('hi'); }\n"
        "document.addEventListener('click', main);\n```"
    )
    result = _parse_code_response(raw)
    assert "<!DOCTYPE html>" in result["index.html"]
    assert "margin" in result["style.css"]
    assert "function" in result["core.js"]


def test_parse_code_response_empty():
    result = _parse_code_response("No code blocks here")
    assert result["index.html"] == ""
    assert result["style.css"] == ""
    assert result["core.js"] == ""


def test_parse_code_response_file_markers():
    raw = (
        "<!-- FILE: index.html -->\n"
        "<!DOCTYPE html><html><body></body></html>\n"
        "<!-- FILE: style.css -->\n"
        "body { color: red; }\n"
        "<!-- FILE: core.js -->\n"
        "function run() {}\n"
    )
    result = _parse_code_response(raw)
    assert "<!DOCTYPE html>" in result["index.html"]
    assert "color: red" in result["style.css"]
    assert "function run" in result["core.js"]


# ── Generate ────────────────────────────────────────────────────────────────


def test_generate_returns_three_files():
    with patch("intention_graph.game_code_generator.anthropic.Anthropic"):
        gen = GameCodeGenerator(api_key="test-key")

    gen._client.messages.stream.return_value = _mock_stream(_SAMPLE_CODE_RESPONSE)

    result = gen.generate(_SAMPLE_PRD, _SAMPLE_WIREFRAME)

    assert "index.html" in result
    assert "style.css" in result
    assert "core.js" in result
    assert "<!DOCTYPE html>" in result["index.html"]


def test_generate_html_has_screen_divs():
    with patch("intention_graph.game_code_generator.anthropic.Anthropic"):
        gen = GameCodeGenerator(api_key="test-key")

    gen._client.messages.stream.return_value = _mock_stream(_SAMPLE_CODE_RESPONSE)

    result = gen.generate(_SAMPLE_PRD, _SAMPLE_WIREFRAME)

    html = result["index.html"]
    assert 'id="start_screen"' in html
    assert 'id="gameplay"' in html
    assert 'id="game_over"' in html


def test_generate_calls_llm_once():
    with patch("intention_graph.game_code_generator.anthropic.Anthropic"):
        gen = GameCodeGenerator(api_key="test-key")

    gen._client.messages.stream.return_value = _mock_stream(_SAMPLE_CODE_RESPONSE)

    gen.generate(_SAMPLE_PRD, _SAMPLE_WIREFRAME)
    gen._client.messages.stream.assert_called_once()


def test_generate_with_reference_code():
    with patch("intention_graph.game_code_generator.anthropic.Anthropic"):
        gen = GameCodeGenerator(api_key="test-key")

    gen._client.messages.stream.return_value = _mock_stream(_SAMPLE_CODE_RESPONSE)

    gen.generate(_SAMPLE_PRD, _SAMPLE_WIREFRAME, reference_code="<html>ref</html>")

    call_args = gen._client.messages.stream.call_args
    user_msg = call_args.kwargs["messages"][0]["content"]
    assert "Reference Code" in user_msg


def test_generate_without_reference():
    with patch("intention_graph.game_code_generator.anthropic.Anthropic"):
        gen = GameCodeGenerator(api_key="test-key")

    gen._client.messages.stream.return_value = _mock_stream(_SAMPLE_CODE_RESPONSE)

    gen.generate(_SAMPLE_PRD, _SAMPLE_WIREFRAME)

    call_args = gen._client.messages.stream.call_args
    user_msg = call_args.kwargs["messages"][0]["content"]
    assert "Reference Code" not in user_msg


def test_generate_system_prompt_includes_wireframe():
    with patch("intention_graph.game_code_generator.anthropic.Anthropic"):
        gen = GameCodeGenerator(api_key="test-key")

    gen._client.messages.stream.return_value = _mock_stream(_SAMPLE_CODE_RESPONSE)

    gen.generate(_SAMPLE_PRD, _SAMPLE_WIREFRAME)

    call_args = gen._client.messages.stream.call_args
    user_msg = call_args.kwargs["messages"][0]["content"]
    assert "start_screen" in user_msg
    assert "gameplay" in user_msg


# ── Integration ──────────────────────────────────────────────────────────────


@pytest.fixture
def game_code_generator():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return GameCodeGenerator(api_key=api_key)


@pytest.mark.slow
def test_integration_generate(game_code_generator):
    result = game_code_generator.generate(_SAMPLE_PRD, _SAMPLE_WIREFRAME)

    assert "index.html" in result
    assert "style.css" in result
    assert "core.js" in result
    assert len(result["index.html"]) > 100
    assert len(result["core.js"]) > 100
