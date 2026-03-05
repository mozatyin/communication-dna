"""Tests for InterfacePlanGenerator (Stage 1)."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from intention_graph.interface_plan_generator import (
    InterfacePlanGenerator,
    _parse_json,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _mock_llm_response(text: str) -> MagicMock:
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = text
    mock_response.content = [mock_content]
    return mock_response


_SAMPLE_PLAN_JSON = json.dumps({
    "game_title": "Flappy Bird",
    "art_style": "复古像素风",
    "global_resolution": {"width": 1080, "height": 1920},
    "total_interfaces": 3,
    "entry_interface": "start_screen",
    "interfaces": [
        {
            "index": 1, "id": "start_screen", "name": "开始界面",
            "type": "page",
            "dimensions": {"width": 1080, "height": 1920},
            "description": "标题和开始按钮",
            "belongs_to": None,
            "navigation_from": [], "navigation_to": ["gameplay"],
        },
        {
            "index": 2, "id": "gameplay", "name": "游戏主界面",
            "type": "page",
            "dimensions": {"width": 1080, "height": 1920},
            "description": "核心游戏画面",
            "belongs_to": None,
            "navigation_from": ["start_screen"], "navigation_to": ["game_over"],
        },
        {
            "index": 3, "id": "game_over", "name": "结束界面",
            "type": "page",
            "dimensions": {"width": 1080, "height": 1920},
            "description": "得分和重新开始",
            "belongs_to": None,
            "navigation_from": ["gameplay"], "navigation_to": ["start_screen"],
        },
    ],
})

_SAMPLE_PRD = """
## 1. 游戏总览
**游戏体验**：你是一只小鸟，点击屏幕飞过管道。
**类型与视角**：横版2D休闲游戏。

## 2. 核心游戏循环
**玩家的即时操作**：点击屏幕，小鸟跳起。
**胜利/失败/进程条件**：撞到管道或地面游戏结束。

## 3. 游戏系统
### 飞行控制系统
**如何运作**: 点击屏幕小鸟上升。
### 计分系统
**如何运作**: 通过管道+1分。

## 4. 美术与音效风格
**视觉风格**: 像素风。
"""


# ── Unit Tests ────────────────────────────────────────────────────────────────


def test_parse_json_clean():
    result = _parse_json('{"key": "value"}')
    assert result == {"key": "value"}


def test_parse_json_with_markdown():
    result = _parse_json('```json\n{"key": "value"}\n```')
    assert result == {"key": "value"}


def test_parse_json_with_extra_text():
    result = _parse_json('Here is the JSON:\n{"key": "value"}\nDone.')
    assert result == {"key": "value"}


def test_parse_json_invalid():
    result = _parse_json("not json at all")
    assert result == {}


def test_generator_construction():
    with patch("intention_graph.interface_plan_generator.anthropic.Anthropic"):
        gen = InterfacePlanGenerator(api_key="test-key")
    assert gen._model == "claude-sonnet-4-20250514"


def test_generator_openrouter_detection():
    with patch("intention_graph.interface_plan_generator.anthropic.Anthropic") as mock_cls:
        InterfacePlanGenerator(api_key="sk-or-test")
    call_kwargs = mock_cls.call_args.kwargs
    assert call_kwargs["base_url"] == "https://openrouter.ai/api"


def test_generate_returns_plan():
    with patch("intention_graph.interface_plan_generator.anthropic.Anthropic"):
        gen = InterfacePlanGenerator(api_key="test-key")

    gen._client.messages.create.return_value = _mock_llm_response(
        _SAMPLE_PLAN_JSON
    )

    result = gen.generate(_SAMPLE_PRD)

    assert result["game_title"] == "Flappy Bird"
    assert result["total_interfaces"] == 3
    assert len(result["interfaces"]) == 3
    assert result["entry_interface"] == "start_screen"


def test_generate_calls_llm_once():
    with patch("intention_graph.interface_plan_generator.anthropic.Anthropic"):
        gen = InterfacePlanGenerator(api_key="test-key")

    gen._client.messages.create.return_value = _mock_llm_response(
        _SAMPLE_PLAN_JSON
    )

    gen.generate(_SAMPLE_PRD)

    gen._client.messages.create.assert_called_once()


def test_generate_includes_prd_in_prompt():
    with patch("intention_graph.interface_plan_generator.anthropic.Anthropic"):
        gen = InterfacePlanGenerator(api_key="test-key")

    gen._client.messages.create.return_value = _mock_llm_response(
        _SAMPLE_PLAN_JSON
    )

    gen.generate(_SAMPLE_PRD)

    call_args = gen._client.messages.create.call_args
    user_msg = call_args.kwargs["messages"][0]["content"]
    assert "游戏总览" in user_msg
    assert "飞行控制系统" in user_msg


def test_generate_has_navigation():
    with patch("intention_graph.interface_plan_generator.anthropic.Anthropic"):
        gen = InterfacePlanGenerator(api_key="test-key")

    gen._client.messages.create.return_value = _mock_llm_response(
        _SAMPLE_PLAN_JSON
    )

    result = gen.generate(_SAMPLE_PRD)

    gameplay = next(i for i in result["interfaces"] if i["id"] == "gameplay")
    assert "start_screen" in gameplay["navigation_from"]
    assert "game_over" in gameplay["navigation_to"]


# ── Integration Test ──────────────────────────────────────────────────────────


@pytest.fixture
def plan_generator():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return InterfacePlanGenerator(api_key=api_key)


@pytest.mark.slow
def test_integration_flappy_bird(plan_generator):
    result = plan_generator.generate(_SAMPLE_PRD)

    assert "interfaces" in result
    assert len(result["interfaces"]) >= 2
    assert result.get("entry_interface")

    # Check all interfaces have required fields
    for iface in result["interfaces"]:
        assert "id" in iface
        assert "name" in iface
        assert "type" in iface
        assert iface["type"] in ("page", "popup")
