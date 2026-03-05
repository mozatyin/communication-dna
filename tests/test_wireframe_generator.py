"""Tests for WireframeGenerator (Stage 3)."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from intention_graph.wireframe_generator import WireframeGenerator


def _mock_llm_response(text: str) -> MagicMock:
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = text
    mock_response.content = [mock_content]
    return mock_response


_SAMPLE_WIREFRAME = json.dumps({
    "project": {
        "title": "Flappy Bird",
        "global_resolution": {"width": 1080, "height": 1920},
    },
    "asset_library": {
        "bg_sky": {"type": "image", "path": "assets/images/bg_sky.png", "label": "天空"},
    },
    "modules": [
        {
            "module_id": "menu", "module_name": "菜单",
            "description": "菜单流程", "color": "#4A90D9",
            "interface_ids": ["start"],
        },
    ],
    "module_connections": [],
    "interfaces": [
        {
            "interface_id": "start",
            "interface_name": "开始",
            "module_id": "menu",
            "type": "page",
            "parents": [],
            "children": ["gameplay"],
            "dimensions": {"width": 1080, "height": 1920},
            "elements": [
                {
                    "id": "bg", "type": "image", "asset_id": "bg_sky",
                    "inner_text": None,
                    "rect": {"x": 0, "y": 0, "width": 1080, "height": 1920, "z_index": 0},
                    "style": {"opacity": 1},
                    "event": None, "target_interface_id": None,
                    "element_class": "editable",
                },
                {
                    "id": "btn_play", "type": "button", "asset_id": None,
                    "inner_text": "Play",
                    "rect": {"x": 340, "y": 1000, "width": 400, "height": 100, "z_index": 2},
                    "style": {"background-color": "#E8A43A"},
                    "event": "click", "target_interface_id": "gameplay",
                    "element_class": "editable",
                },
            ],
            "bg_music_asset_id": None,
        },
    ],
})

_SAMPLE_PRD = "## 1. 游戏总览\n点击飞行的小鸟游戏。"

_SAMPLE_PLAN = {
    "game_title": "Flappy Bird",
    "interfaces": [{"id": "start", "name": "开始", "type": "page"}],
}

_SAMPLE_ASSETS = {
    "schemaVersion": "asset-table-1.1",
    "meta": {"gameTitle": "Flappy Bird"},
    "assets": [
        {"id": "bg_sky", "type": "image", "category": "background"},
    ],
}


def test_generator_construction():
    with patch("intention_graph.wireframe_generator.anthropic.Anthropic"):
        gen = WireframeGenerator(api_key="test-key")
    assert gen._model == "claude-sonnet-4-20250514"


def test_generate_returns_wireframe():
    with patch("intention_graph.wireframe_generator.anthropic.Anthropic"):
        gen = WireframeGenerator(api_key="test-key")

    gen._client.messages.create.return_value = _mock_llm_response(
        _SAMPLE_WIREFRAME
    )

    result = gen.generate(_SAMPLE_PRD, _SAMPLE_PLAN, _SAMPLE_ASSETS)

    assert result["project"]["title"] == "Flappy Bird"
    assert len(result["interfaces"]) == 1
    assert "bg_sky" in result["asset_library"]


def test_generate_has_elements():
    with patch("intention_graph.wireframe_generator.anthropic.Anthropic"):
        gen = WireframeGenerator(api_key="test-key")

    gen._client.messages.create.return_value = _mock_llm_response(
        _SAMPLE_WIREFRAME
    )

    result = gen.generate(_SAMPLE_PRD, _SAMPLE_PLAN, _SAMPLE_ASSETS)

    start = result["interfaces"][0]
    assert len(start["elements"]) >= 2

    btn = next(e for e in start["elements"] if e["type"] == "button")
    assert btn["event"] == "click"
    assert btn["target_interface_id"] == "gameplay"


def test_generate_calls_llm_once():
    with patch("intention_graph.wireframe_generator.anthropic.Anthropic"):
        gen = WireframeGenerator(api_key="test-key")

    gen._client.messages.create.return_value = _mock_llm_response(
        _SAMPLE_WIREFRAME
    )

    gen.generate(_SAMPLE_PRD, _SAMPLE_PLAN, _SAMPLE_ASSETS)
    gen._client.messages.create.assert_called_once()


def test_generate_with_reference():
    with patch("intention_graph.wireframe_generator.anthropic.Anthropic"):
        gen = WireframeGenerator(api_key="test-key")

    gen._client.messages.create.return_value = _mock_llm_response(
        _SAMPLE_WIREFRAME
    )

    reference = json.loads(_SAMPLE_WIREFRAME)
    gen.generate(_SAMPLE_PRD, _SAMPLE_PLAN, _SAMPLE_ASSETS, reference_wireframe=reference)

    call_args = gen._client.messages.create.call_args
    user_msg = call_args.kwargs["messages"][0]["content"]
    assert "Golden Sample" in user_msg


def test_generate_without_reference():
    with patch("intention_graph.wireframe_generator.anthropic.Anthropic"):
        gen = WireframeGenerator(api_key="test-key")

    gen._client.messages.create.return_value = _mock_llm_response(
        _SAMPLE_WIREFRAME
    )

    gen.generate(_SAMPLE_PRD, _SAMPLE_PLAN, _SAMPLE_ASSETS)

    call_args = gen._client.messages.create.call_args
    user_msg = call_args.kwargs["messages"][0]["content"]
    assert "Golden Sample" not in user_msg


# ── Integration ──────────────────────────────────────────────────────────────


@pytest.fixture
def wireframe_generator():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return WireframeGenerator(api_key=api_key)


@pytest.mark.slow
def test_integration_generate(wireframe_generator):
    result = wireframe_generator.generate(_SAMPLE_PRD, _SAMPLE_PLAN, _SAMPLE_ASSETS)

    assert "interfaces" in result
    assert len(result["interfaces"]) >= 1
    for iface in result["interfaces"]:
        assert "interface_id" in iface
        assert "elements" in iface
        assert len(iface["elements"]) >= 1
