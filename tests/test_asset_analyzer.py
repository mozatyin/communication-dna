"""Tests for AssetAnalyzer (Stage 2.1)."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from intention_graph.asset_analyzer import AssetAnalyzer


def _mock_llm_response(text: str) -> MagicMock:
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = text
    mock_response.content = [mock_content]
    return mock_response


_SAMPLE_ASSET_TABLE = json.dumps({
    "schemaVersion": "asset-table-1.1",
    "meta": {"gameTitle": "Flappy Bird", "artDirection": "像素风"},
    "assets": [
        {
            "id": "bg_sky", "type": "image", "category": "background",
            "usage": "所有界面背景", "description": "蓝天白云",
            "implementation": "image",
            "dimensions": {"width": 1080, "height": 1920},
            "default_label": "", "format": "png",
            "path": "assets/images/bg_sky.png",
        },
        {
            "id": "btn_start", "type": "image", "category": "ui",
            "usage": "开始按钮", "description": "开始游戏按钮",
            "implementation": "css",
            "dimensions": None,
            "default_label": "Play", "format": "png",
            "path": "",
        },
        {
            "id": "sfx_flap", "type": "audio", "category": "sfx",
            "usage": "点击跳跃", "description": "翅膀扇动声",
            "implementation": "audio",
            "dimensions": None,
            "default_label": "", "format": "mp3",
            "path": "assets/audio/sfx_flap.mp3",
        },
    ],
})

_SAMPLE_PRD = "## 1. 游戏总览\n点击飞行的小鸟游戏。"

_SAMPLE_PLAN = {
    "game_title": "Flappy Bird",
    "interfaces": [
        {"id": "start", "name": "开始", "type": "page"},
        {"id": "gameplay", "name": "游戏", "type": "page"},
    ],
}


def test_analyzer_construction():
    with patch("intention_graph.asset_analyzer.anthropic.Anthropic"):
        analyzer = AssetAnalyzer(api_key="test-key")
    assert analyzer._model == "claude-sonnet-4-20250514"


def test_analyze_returns_asset_table():
    with patch("intention_graph.asset_analyzer.anthropic.Anthropic"):
        analyzer = AssetAnalyzer(api_key="test-key")

    analyzer._client.messages.create.return_value = _mock_llm_response(
        _SAMPLE_ASSET_TABLE
    )

    result = analyzer.analyze(_SAMPLE_PRD, _SAMPLE_PLAN)

    assert result["schemaVersion"] == "asset-table-1.1"
    assert len(result["assets"]) == 3
    assert result["meta"]["gameTitle"] == "Flappy Bird"


def test_analyze_includes_prd_and_plan():
    with patch("intention_graph.asset_analyzer.anthropic.Anthropic"):
        analyzer = AssetAnalyzer(api_key="test-key")

    analyzer._client.messages.create.return_value = _mock_llm_response(
        _SAMPLE_ASSET_TABLE
    )

    analyzer.analyze(_SAMPLE_PRD, _SAMPLE_PLAN)

    call_args = analyzer._client.messages.create.call_args
    user_msg = call_args.kwargs["messages"][0]["content"]
    assert "游戏总览" in user_msg
    assert "Flappy Bird" in user_msg


def test_analyze_calls_llm_once():
    with patch("intention_graph.asset_analyzer.anthropic.Anthropic"):
        analyzer = AssetAnalyzer(api_key="test-key")

    analyzer._client.messages.create.return_value = _mock_llm_response(
        _SAMPLE_ASSET_TABLE
    )

    analyzer.analyze(_SAMPLE_PRD, _SAMPLE_PLAN)
    analyzer._client.messages.create.assert_called_once()


def test_analyze_asset_types():
    with patch("intention_graph.asset_analyzer.anthropic.Anthropic"):
        analyzer = AssetAnalyzer(api_key="test-key")

    analyzer._client.messages.create.return_value = _mock_llm_response(
        _SAMPLE_ASSET_TABLE
    )

    result = analyzer.analyze(_SAMPLE_PRD, _SAMPLE_PLAN)
    types = {a["type"] for a in result["assets"]}
    assert "image" in types
    assert "audio" in types


# ── Integration ──────────────────────────────────────────────────────────────


@pytest.fixture
def asset_analyzer():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return AssetAnalyzer(api_key=api_key)


@pytest.mark.slow
def test_integration_analyze(asset_analyzer):
    result = asset_analyzer.analyze(_SAMPLE_PRD, _SAMPLE_PLAN)
    assert "assets" in result
    assert len(result["assets"]) >= 1
    for asset in result["assets"]:
        assert "id" in asset
        assert "type" in asset
