"""Tests for game code quality evaluation."""

from intention_graph.wireframe_quality import QualityMetric, QualityReport
from intention_graph.game_code_quality import (
    evaluate,
    _check_file_completeness,
    _check_html_validity,
    _check_js_syntax,
    _check_css_reference_integrity,
    _check_screen_coverage,
    _check_element_coverage,
    _check_style_fidelity,
    _check_navigation_integrity,
    _extract_html_elements,
    _extract_js_summary,
    _count_canvas_elements,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


_SAMPLE_HTML = """\
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Flappy Bird</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div id="start_screen" class="screen">
        <h1 id="title">Flappy Bird</h1>
        <button id="btn_play" class="btn" onclick="showScreen('gameplay')">Play</button>
        <button id="btn_leaderboard" class="btn" onclick="showScreen('leaderboard')">Leaderboard</button>
    </div>
    <div id="gameplay" class="screen" style="display:none">
        <canvas id="game_canvas" width="1080" height="1920"></canvas>
        <div id="score_display" class="hud">0</div>
    </div>
    <div id="game_over" class="screen" style="display:none">
        <h2 id="gameover_text">Game Over</h2>
        <div id="final_score">Score: 0</div>
        <button id="btn_retry" class="btn" onclick="showScreen('gameplay')">Retry</button>
        <button id="btn_menu" class="btn" onclick="showScreen('start_screen')">Menu</button>
    </div>
    <script src="core.js"></script>
</body>
</html>
"""

_SAMPLE_CSS = """\
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background-color: #4EC0CA; font-family: Arial, sans-serif; }
.screen { width: 1080px; height: 1920px; position: relative; }
#start_screen { background-color: #4EC0CA; }
#title { color: #FFFFFF; font-size: 48px; text-align: center; }
.btn { background-color: #E8A43A; color: white; border: none; padding: 20px 40px;
       font-size: 24px; border-radius: 10px; cursor: pointer; }
#gameplay { background-color: #70C5CE; }
.hud { color: #FFFFFF; font-size: 36px; position: absolute; top: 20px; }
#game_over { background-color: #DED895; text-align: center; }
#gameover_text { color: #503D18; font-size: 40px; }
#final_score { color: #503D18; font-size: 32px; }
"""

_SAMPLE_JS = """\
const screens = document.querySelectorAll('.screen');

function showScreen(id) {
    screens.forEach(s => s.style.display = 'none');
    document.getElementById(id).style.display = 'block';
}

const canvas = document.getElementById('game_canvas');
const ctx = canvas.getContext('2d');

let bird = { x: 200, y: 400, velocity: 0, gravity: 0.5 };
let pipes = [];
let score = 0;
let gameRunning = false;

function startGame() {
    bird = { x: 200, y: 400, velocity: 0, gravity: 0.5 };
    pipes = [];
    score = 0;
    gameRunning = true;
    showScreen('gameplay');
    gameLoop();
}

function gameLoop() {
    if (!gameRunning) return;
    update();
    draw();
    requestAnimationFrame(gameLoop);
}

function update() {
    bird.velocity += bird.gravity;
    bird.y += bird.velocity;
    if (bird.y > canvas.height || bird.y < 0) {
        gameOver();
    }
}

function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#FFD700';
    ctx.fillRect(bird.x, bird.y, 40, 40);
}

function gameOver() {
    gameRunning = false;
    document.getElementById('final_score').textContent = 'Score: ' + score;
    showScreen('game_over');
}

document.addEventListener('keydown', function(e) {
    if (e.code === 'Space' && gameRunning) {
        bird.velocity = -8;
    }
});

canvas.addEventListener('click', function() {
    if (gameRunning) {
        bird.velocity = -8;
    }
});
"""

_SAMPLE_WIREFRAME = {
    "project": {"title": "Flappy Bird", "global_resolution": {"width": 1080, "height": 1920}},
    "interfaces": [
        {
            "interface_id": "start_screen",
            "interface_name": "开始界面",
            "type": "page",
            "parents": [],
            "children": ["gameplay"],
            "elements": [
                {"id": "bg", "type": "image", "rect": {"z_index": 0},
                 "style": {"background-color": "#4EC0CA"}, "event": None},
                {"id": "title_logo", "type": "image", "rect": {"z_index": 1},
                 "style": {}, "event": None},
                {"id": "btn_start", "type": "button", "inner_text": "开始游戏",
                 "rect": {"z_index": 2},
                 "style": {"background-color": "#E8A43A", "font-size": "24px"},
                 "event": "click", "target_interface_id": "gameplay"},
            ],
        },
        {
            "interface_id": "gameplay",
            "interface_name": "游戏界面",
            "type": "page",
            "parents": ["start_screen"],
            "children": ["game_over"],
            "elements": [
                {"id": "bg", "type": "image", "rect": {"z_index": 0},
                 "style": {"background-color": "#70C5CE"}, "event": None},
                {"id": "bird", "type": "image", "rect": {"z_index": 2},
                 "style": {}, "event": None},
                {"id": "score_text", "type": "text", "inner_text": "0",
                 "rect": {"z_index": 3},
                 "style": {"color": "#FFFFFF", "font-size": "36px"}, "event": None},
                {"id": "pipe_top", "type": "image", "rect": {"z_index": 1},
                 "style": {}, "event": None},
                {"id": "pipe_bottom", "type": "image", "rect": {"z_index": 1},
                 "style": {}, "event": None},
            ],
        },
        {
            "interface_id": "game_over",
            "interface_name": "结算界面",
            "type": "page",
            "parents": ["gameplay"],
            "children": ["start_screen", "gameplay"],
            "elements": [
                {"id": "bg", "type": "image", "rect": {"z_index": 0},
                 "style": {"background-color": "#DED895"}, "event": None},
                {"id": "gameover_text", "type": "image", "rect": {"z_index": 1},
                 "style": {}, "event": None},
                {"id": "score_panel", "type": "image", "rect": {"z_index": 1},
                 "style": {}, "event": None},
                {"id": "btn_retry", "type": "button", "inner_text": "重新开始",
                 "rect": {"z_index": 2},
                 "style": {"background-color": "#E8A43A"},
                 "event": "click", "target_interface_id": "gameplay"},
                {"id": "btn_menu", "type": "button", "inner_text": "主菜单",
                 "rect": {"z_index": 2},
                 "style": {"background-color": "#E8A43A"},
                 "event": "click", "target_interface_id": "start_screen"},
            ],
        },
    ],
}


# ── HTML Element Extraction ─────────────────────────────────────────────────


def test_extract_html_elements():
    elements = _extract_html_elements(_SAMPLE_HTML)
    tags = [e["tag"] for e in elements]
    assert "button" in tags
    assert "canvas" in tags
    assert "div" in tags


def test_extract_html_elements_empty():
    elements = _extract_html_elements("")
    assert elements == []


# ── Layer 1: File Completeness ──────────────────────────────────────────────


def test_file_completeness_perfect():
    result = _check_file_completeness(_SAMPLE_HTML, _SAMPLE_CSS, _SAMPLE_JS)
    assert result.passed is True
    assert result.score == 1.0


def test_file_completeness_empty_css():
    result = _check_file_completeness(_SAMPLE_HTML, "", _SAMPLE_JS)
    assert result.passed is False
    assert result.score < 1.0


def test_file_completeness_all_empty():
    result = _check_file_completeness("", "", "")
    assert result.passed is False
    assert result.score < 0.5  # 3/5 checks fail, refs skipped when HTML empty


def test_file_completeness_missing_js_ref():
    html_no_js = "<html><head><link rel='stylesheet' href='style.css'></head><body></body></html>"
    result = _check_file_completeness(html_no_js, _SAMPLE_CSS, _SAMPLE_JS)
    assert result.score < 1.0


# ── Layer 1: HTML Validity ──────────────────────────────────────────────────


def test_html_validity_good():
    result = _check_html_validity(_SAMPLE_HTML)
    assert result.passed is True
    assert result.score == 1.0


def test_html_validity_empty():
    result = _check_html_validity("")
    assert result.passed is False
    assert result.score == 0.0


def test_html_validity_minimal():
    html = "<html><head></head><body><div>hello</div></body></html>"
    result = _check_html_validity(html)
    assert result.score >= 0.5  # missing DOCTYPE but has structure


# ── Layer 1: JS Syntax ─────────────────────────────────────────────────────


def test_js_syntax_good():
    result = _check_js_syntax(_SAMPLE_JS)
    assert result.passed is True
    assert result.score == 1.0


def test_js_syntax_empty():
    result = _check_js_syntax("")
    assert result.passed is False
    assert result.score == 0.0


def test_js_syntax_unbalanced():
    js = "function foo() { if (true) { console.log('hi'); }"
    result = _check_js_syntax(js)
    assert result.score < 1.0


def test_js_syntax_no_events():
    js = "function foo() { return 1; }"
    result = _check_js_syntax(js)
    assert result.score < 1.0  # no event listeners


# ── Layer 1: CSS Reference Integrity ───────────────────────────────────────


def test_css_ref_integrity_good():
    result = _check_css_reference_integrity(_SAMPLE_HTML, _SAMPLE_CSS)
    assert result.passed is True
    assert result.score > 0.3


def test_css_ref_integrity_empty():
    result = _check_css_reference_integrity("", "")
    assert result.passed is False


def test_css_ref_integrity_no_matches():
    html = '<div id="foo" class="bar baz"></div>'
    css = "body { color: red; }"
    result = _check_css_reference_integrity(html, css)
    assert result.score == 0.0


# ── Layer 2: Screen Coverage ────────────────────────────────────────────────


def test_screen_coverage_perfect():
    result = _check_screen_coverage(_SAMPLE_HTML, _SAMPLE_WIREFRAME)
    assert result.passed is True
    assert result.score == 1.0


def test_screen_coverage_partial():
    wf = {
        "interfaces": [
            {"interface_id": "start_screen"},
            {"interface_id": "gameplay"},
            {"interface_id": "game_over"},
            {"interface_id": "settings"},  # not in HTML
        ],
    }
    result = _check_screen_coverage(_SAMPLE_HTML, wf)
    assert result.score == 0.75  # 3/4


def test_screen_coverage_none():
    wf = {"interfaces": [{"interface_id": "nonexistent_screen"}]}
    result = _check_screen_coverage(_SAMPLE_HTML, wf)
    assert result.score == 0.0


def test_screen_coverage_empty_wireframe():
    result = _check_screen_coverage(_SAMPLE_HTML, {"interfaces": []})
    assert result.passed is True
    assert result.score == 1.0


# ── Layer 2: Element Coverage ──────────────────────────────────────────────


def test_element_coverage_good():
    result = _check_element_coverage(_SAMPLE_HTML, _SAMPLE_WIREFRAME)
    assert result.passed is True
    assert result.score > 0.0


def test_element_coverage_empty_wireframe():
    result = _check_element_coverage(_SAMPLE_HTML, {"interfaces": []})
    assert result.passed is True
    assert result.score == 1.0


# ── Layer 2: Style Fidelity ────────────────────────────────────────────────


def test_style_fidelity_good():
    result = _check_style_fidelity(_SAMPLE_CSS, _SAMPLE_HTML, _SAMPLE_WIREFRAME)
    assert result.passed is True
    assert result.score > 0.3


def test_style_fidelity_empty_css():
    result = _check_style_fidelity("", _SAMPLE_HTML, _SAMPLE_WIREFRAME)
    assert result.passed is False
    assert result.score == 0.0


def test_style_fidelity_no_wireframe_styles():
    wf = {"interfaces": [{"interface_id": "x", "elements": [{"id": "a", "style": {}}]}]}
    result = _check_style_fidelity(_SAMPLE_CSS, _SAMPLE_HTML, wf)
    assert result.passed is True  # nothing to check


# ── Layer 2: Navigation Integrity ──────────────────────────────────────────


def test_navigation_integrity_good():
    result = _check_navigation_integrity(_SAMPLE_HTML, _SAMPLE_JS, _SAMPLE_WIREFRAME)
    assert result.passed is True
    assert result.score > 0.5


def test_navigation_integrity_empty_js():
    result = _check_navigation_integrity(_SAMPLE_HTML, "", _SAMPLE_WIREFRAME)
    # HTML has onclick with screen IDs, so some should still match
    assert result.score >= 0.0


def test_navigation_integrity_no_edges():
    wf = {"interfaces": [{"interface_id": "x", "children": [], "elements": []}]}
    result = _check_navigation_integrity(_SAMPLE_HTML, _SAMPLE_JS, wf)
    assert result.passed is True


# ── Full evaluate ────────────────────────────────────────────────────────────


def test_evaluate_good():
    report = evaluate(_SAMPLE_HTML, _SAMPLE_CSS, _SAMPLE_JS, _SAMPLE_WIREFRAME)
    assert report.overall_score > 0.5
    assert len(report.metrics) == 8


def test_evaluate_empty():
    report = evaluate("", "", "", _SAMPLE_WIREFRAME)
    assert report.overall_score < 0.5


def test_evaluate_report_has_critical_metrics():
    report = evaluate(_SAMPLE_HTML, _SAMPLE_CSS, _SAMPLE_JS, _SAMPLE_WIREFRAME)
    metric_names = [m.name for m in report.metrics]
    assert "file_completeness" in metric_names
    assert "screen_coverage" in metric_names


# ── JS Summary Extraction ─────────────────────────────────────────────────


def test_extract_js_summary_captures_functions():
    summary = _extract_js_summary(_SAMPLE_JS)
    for name in ["showScreen", "startGame", "gameLoop", "update", "draw", "gameOver"]:
        assert name in summary, f"Missing function: {name}"


def test_extract_js_summary_captures_canvas():
    summary = _extract_js_summary(_SAMPLE_JS)
    assert "fillRect" in summary
    assert "clearRect" in summary


def test_extract_js_summary_captures_events():
    summary = _extract_js_summary(_SAMPLE_JS)
    assert "keydown" in summary
    assert "click" in summary


def test_extract_js_summary_captures_state():
    summary = _extract_js_summary(_SAMPLE_JS)
    assert "bird" in summary
    assert "pipes" in summary
    assert "score" in summary


def test_extract_js_summary_max_chars():
    big_js = "function f() { return 1; }\n" * 500
    summary = _extract_js_summary(big_js, max_chars=2000)
    assert len(summary) <= 2000


def test_extract_js_summary_empty():
    summary = _extract_js_summary("")
    assert len(summary) > 0  # returns "(empty JS)"
    summary2 = _extract_js_summary("   ")
    assert len(summary2) > 0


# ── Canvas Element Counting ───────────────────────────────────────────────


def test_count_canvas_elements_basic():
    js = """
    ctx.fillStyle = '#FFD700';
    ctx.fillRect(10, 10, 40, 40);
    ctx.fillStyle = '#00FF00';
    ctx.fillRect(100, 100, 20, 20);
    ctx.fillStyle = '#FF0000';
    ctx.fillRect(200, 200, 30, 30);
    ctx.fillText('Score: 0', 10, 30);
    """
    count = _count_canvas_elements(js)
    assert count >= 2


def test_count_canvas_elements_draw_image():
    js = """
    ctx.drawImage(birdImg, 10, 10);
    ctx.drawImage(pipeImg, 50, 50);
    """
    count = _count_canvas_elements(js)
    assert count >= 1


def test_count_canvas_elements_empty():
    assert _count_canvas_elements("") == 0
    assert _count_canvas_elements("let x = 1;") == 0


def test_element_coverage_with_canvas():
    """Gameplay screen should get higher count when JS canvas elements are included."""
    result_without = _check_element_coverage(_SAMPLE_HTML, _SAMPLE_WIREFRAME, js="")
    result_with = _check_element_coverage(_SAMPLE_HTML, _SAMPLE_WIREFRAME, js=_SAMPLE_JS)
    # With JS, gameplay canvas elements are counted, so score should be >= without
    assert result_with.score >= result_without.score
