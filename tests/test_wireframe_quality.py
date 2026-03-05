"""Tests for wireframe quality evaluation."""

import json

from intention_graph.wireframe_quality import (
    QualityMetric,
    QualityReport,
    evaluate,
    _match_screens,
    _check_screen_coverage,
    _check_element_coverage,
    _check_navigation_accuracy,
    _check_layout_completeness,
    _check_element_types,
    _extract_nav_edges,
    _wireframe_summary,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


_GOLDEN = {
    "project": {"title": "Test", "global_resolution": {"width": 1080, "height": 1920}},
    "interfaces": [
        {
            "interface_id": "start",
            "interface_name": "Start",
            "type": "page",
            "parents": [],
            "children": ["gameplay"],
            "elements": [
                {"id": "bg", "type": "image", "asset_id": "bg1",
                 "rect": {"x": 0, "y": 0, "width": 1080, "height": 1920, "z_index": 0},
                 "style": {}, "event": None, "target_interface_id": None},
                {"id": "btn", "type": "button", "inner_text": "Play",
                 "rect": {"x": 340, "y": 900, "width": 400, "height": 100, "z_index": 1},
                 "style": {}, "event": "click", "target_interface_id": "gameplay"},
            ],
        },
        {
            "interface_id": "gameplay",
            "interface_name": "Game",
            "type": "page",
            "parents": ["start"],
            "children": ["game_over"],
            "elements": [
                {"id": "bg", "type": "image", "asset_id": "bg2",
                 "rect": {"x": 0, "y": 0, "width": 1080, "height": 1920, "z_index": 0},
                 "style": {}, "event": None, "target_interface_id": None},
                {"id": "score", "type": "text", "inner_text": "0",
                 "rect": {"x": 440, "y": 100, "width": 200, "height": 80, "z_index": 1},
                 "style": {}, "event": None, "target_interface_id": None},
                {"id": "tap", "type": "button", "inner_text": None,
                 "rect": {"x": 0, "y": 0, "width": 1080, "height": 1920, "z_index": 2},
                 "style": {"opacity": 0}, "event": "click", "target_interface_id": None},
            ],
        },
        {
            "interface_id": "game_over",
            "interface_name": "Game Over",
            "type": "page",
            "parents": ["gameplay"],
            "children": ["start"],
            "elements": [
                {"id": "bg", "type": "image", "asset_id": "bg1",
                 "rect": {"x": 0, "y": 0, "width": 1080, "height": 1920, "z_index": 0},
                 "style": {}, "event": None, "target_interface_id": None},
                {"id": "text", "type": "text", "inner_text": "Game Over",
                 "rect": {"x": 240, "y": 400, "width": 600, "height": 100, "z_index": 1},
                 "style": {}, "event": None, "target_interface_id": None},
                {"id": "btn_retry", "type": "button", "inner_text": "Retry",
                 "rect": {"x": 340, "y": 900, "width": 400, "height": 100, "z_index": 1},
                 "style": {}, "event": "click", "target_interface_id": "start"},
            ],
        },
    ],
}


# ── QualityReport tests ──────────────────────────────────────────────────────


def test_report_overall_score():
    report = QualityReport(metrics=[
        QualityMetric(name="a", passed=True, score=1.0),
        QualityMetric(name="b", passed=True, score=0.5),
    ])
    assert report.overall_score == 0.75


def test_report_passed():
    report = QualityReport(metrics=[
        QualityMetric(name="screen_coverage", passed=True, score=1.0),
        QualityMetric(name="navigation_accuracy", passed=True, score=1.0),
        QualityMetric(name="other", passed=False, score=0.3),
    ])
    assert report.passed is True  # non-critical failure


def test_report_fails_critical():
    report = QualityReport(metrics=[
        QualityMetric(name="screen_coverage", passed=False, score=0.3),
    ])
    assert report.passed is False


def test_report_summary():
    report = QualityReport(metrics=[
        QualityMetric(name="test", passed=True, score=1.0, detail="ok"),
    ])
    assert "PASS" in report.summary()


# ── Fuzzy matching ───────────────────────────────────────────────────────────


def test_match_screens_exact_ids():
    matched = _match_screens(_GOLDEN, _GOLDEN)
    assert len(matched) == 3


def test_match_screens_fuzzy():
    gen = {
        "interfaces": [
            {"interface_id": "main_menu", "interface_name": "主菜单", "type": "page"},
            {"interface_id": "gameplay", "interface_name": "游戏", "type": "page"},
            {"interface_id": "game_over", "interface_name": "结束", "type": "page"},
        ],
    }
    gold = {
        "interfaces": [
            {"interface_id": "start_screen", "interface_name": "开始界面", "type": "page"},
            {"interface_id": "gameplay", "interface_name": "Game", "type": "page"},
            {"interface_id": "game_over", "interface_name": "Game Over", "type": "page"},
        ],
    }
    matched = _match_screens(gen, gold)
    assert len(matched) >= 2  # gameplay and game_over should match


# ── Screen coverage ──────────────────────────────────────────────────────────


def test_screen_coverage_perfect_match():
    result = _check_screen_coverage(_GOLDEN, _GOLDEN)
    assert result.passed is True
    assert result.score == 1.0


def test_screen_coverage_partial():
    gen = {
        "interfaces": [
            {"interface_id": "start"},
            {"interface_id": "gameplay"},
        ],
    }
    result = _check_screen_coverage(gen, _GOLDEN)
    assert result.passed is True  # 2/3 overlap
    assert result.score > 0.5


def test_screen_coverage_no_overlap():
    gen = {"interfaces": [{"interface_id": "settings"}]}
    result = _check_screen_coverage(gen, _GOLDEN)
    assert result.score < 0.5


# ── Element coverage ─────────────────────────────────────────────────────────


def test_element_coverage_perfect():
    result = _check_element_coverage(_GOLDEN, _GOLDEN)
    assert result.passed is True
    assert result.score == 1.0


def test_element_coverage_fewer_elements():
    gen = {
        "interfaces": [
            {"interface_id": "start", "elements": [{"id": "bg"}]},
            {"interface_id": "gameplay", "elements": [{"id": "bg"}]},
            {"interface_id": "game_over", "elements": [{"id": "bg"}]},
        ],
    }
    result = _check_element_coverage(gen, _GOLDEN)
    assert result.score < 1.0


# ── Navigation accuracy ─────────────────────────────────────────────────────


def test_nav_edges_extraction():
    edges = _extract_nav_edges(_GOLDEN)
    assert ("start", "gameplay") in edges
    assert ("gameplay", "game_over") in edges
    assert ("game_over", "start") in edges


def test_navigation_perfect():
    result = _check_navigation_accuracy(_GOLDEN, _GOLDEN)
    assert result.passed is True
    assert result.score == 1.0


def test_navigation_missing_edge():
    gen = {
        "interfaces": [
            {"interface_id": "start", "children": ["gameplay"], "elements": []},
            {"interface_id": "gameplay", "children": [], "elements": []},
        ],
    }
    result = _check_navigation_accuracy(gen, _GOLDEN)
    assert result.score < 1.0


# ── Layout completeness ─────────────────────────────────────────────────────


def test_layout_completeness_good():
    result = _check_layout_completeness(_GOLDEN)
    assert result.passed is True


def test_layout_completeness_empty():
    gen = {"interfaces": []}
    result = _check_layout_completeness(gen)
    assert result.passed is False


def test_layout_completeness_missing_bg():
    gen = {
        "interfaces": [{
            "interface_id": "test",
            "elements": [
                {"id": "btn", "type": "button", "inner_text": "Click",
                 "rect": {"z_index": 1}, "event": "click"},
            ],
        }],
    }
    result = _check_layout_completeness(gen)
    assert result.score < 1.0


# ── Element types ────────────────────────────────────────────────────────────


def test_element_types_all_present():
    result = _check_element_types(_GOLDEN)
    assert result.passed is True
    assert result.score == 1.0


def test_element_types_missing():
    gen = {
        "interfaces": [{
            "interface_id": "test",
            "elements": [{"id": "bg", "type": "image"}],
        }],
    }
    result = _check_element_types(gen)
    assert result.score < 1.0


# ── Full evaluate ────────────────────────────────────────────────────────────


def test_evaluate_perfect():
    report = evaluate(_GOLDEN, _GOLDEN)
    assert report.passed is True
    assert report.overall_score >= 0.9


def test_evaluate_empty_gen():
    gen = {"interfaces": []}
    report = evaluate(gen, _GOLDEN)
    assert report.passed is False


# ── Wireframe summary ───────────────────────────────────────────────────────


def test_wireframe_summary_format():
    summary = _wireframe_summary(_GOLDEN)
    assert "Test" in summary
    assert "Screens: 3" in summary
    assert "start" in summary
