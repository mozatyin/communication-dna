"""Tests for browser smoke tests."""

from unittest.mock import patch

import pytest

from intention_graph.wireframe_quality import QualityMetric


_SAMPLE_HTML = """\
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
        <canvas id="game_canvas" width="400" height="300"></canvas>
    </div>
    <div id="game_over" class="screen" style="display:none">
        <h2>Game Over</h2>
        <button onclick="showScreen('start_screen')">Menu</button>
    </div>
    <script src="core.js"></script>
</body>
</html>
"""

_SAMPLE_CSS = """\
* { margin: 0; padding: 0; }
body { background: #333; }
.screen { width: 400px; height: 300px; }
"""

_SAMPLE_JS = """\
const screens = document.querySelectorAll('.screen');

function showScreen(id) {
    screens.forEach(s => s.style.display = 'none');
    document.getElementById(id).style.display = 'block';
}
"""

_SAMPLE_WIREFRAME = {
    "interfaces": [
        {"interface_id": "start_screen", "elements": [], "children": ["gameplay"]},
        {"interface_id": "gameplay", "elements": [], "children": ["game_over"]},
        {"interface_id": "game_over", "elements": [], "children": ["start_screen"]},
    ],
}


def test_browser_smoke_skips_without_playwright():
    """Graceful degradation when playwright is not installed."""
    with patch("intention_graph.game_code_browser_test._HAS_PLAYWRIGHT", False):
        from intention_graph.game_code_browser_test import browser_smoke_test

        result = browser_smoke_test(
            _SAMPLE_HTML, _SAMPLE_CSS, _SAMPLE_JS, _SAMPLE_WIREFRAME,
        )
    assert result.name == "browser_smoke"
    assert result.passed is True  # SKIPPED counts as pass
    assert "SKIPPED" in result.detail


def _playwright_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright
        return True
    except ImportError:
        return False


@pytest.mark.slow
@pytest.mark.skipif(not _playwright_available(), reason="playwright not installed")
def test_browser_smoke_integration():
    """Full Playwright test on sample HTML."""
    from intention_graph.game_code_browser_test import browser_smoke_test

    result = browser_smoke_test(
        _SAMPLE_HTML, _SAMPLE_CSS, _SAMPLE_JS, _SAMPLE_WIREFRAME,
    )
    assert result.name == "browser_smoke"
    assert result.score > 0.0
    # At minimum page_loads and screens_exist should pass
    assert "page_loads=OK" in result.detail
