"""Tests for PRD quality evaluation module."""

import pytest

from intention_graph.prd_quality import (
    QualityMetric,
    QualityReport,
    evaluate,
    evaluate_batch,
    batch_summary,
    _check_completeness,
    _check_length,
    _check_system_count,
    _check_inferred_accuracy,
    _check_banned_phrases,
    _check_faithfulness,
    _check_specificity,
    _check_design_questions,
)
from intention_graph.one_sentence_prd import _COMPLEXITY_PROFILES


# ── Fixture: Sample PRDs ────────────────────────────────────────────────────

_GOOD_PRD = """
## 1. 游戏总览

**游戏体验：** 你是一名驾驶P-38战斗机的飞行员，在太平洋上空与敌军展开激烈空战。

**类型与视角：** 垂直卷轴射击游戏，俯视角度。

**乐趣与吸引力：** 瞬间反馈的射击快感。

## 2. 核心游戏循环

**玩家的即时操作：** 你用方向键控制战机，每秒6发子弹扫射。

**胜利/失败/进程条件：** 击败BOSS即可过关。3条生命用完游戏结束。

**循环的演变、升级与持续吸引力：** 第1小时掌握基础，第10小时追求高分。

## 3. 游戏系统

### 射击系统
**如何运作**: 你按住射击键释放子弹流，每秒约6发。
**为何感觉良好**: 密集射击带来压制感和控制感。
**设计考量**: 射击频率应该多快？如果每秒超过8发会过于混乱。推荐：每秒6发。
**如何连接**: 当你拾取武器升级道具后，射击效果立即变化。

### 强化道具系统
**如何运作**: 击败红色敌机后掉落POW道具。
**为何感觉良好**: 拾取瞬间的强化感带来成长快感。
**设计考量**: 道具掉落率应该多高？推荐80%概率。
**如何连接**: 升级后在射击系统中看到威力变化。

### 计分系统
**如何运作**: 击败敌机获得50-200分基础分数。连续击杀产生x2-x8倍增。
**为何感觉良好**: 连击倍增奖励技巧操作。
**设计考量**: 连击倍增上限应该是多少？推荐x8。
**如何连接**: 更强火力让你更容易维持连击。

### BOSS战斗系统
**如何运作**: 每关末尾出现大型BOSS，拥有500-2000点血量。
**为何感觉良好**: BOSS战提供紧张高潮。
**设计考量**: BOSS血量应该设置多少？推荐500-2000点。
**如何连接**: BOSS战的高分奖励提升排名。

## 4. 美术与音效风格

**视觉风格**: 经典80年代街机像素风格。
**色彩调性**: 深蓝色海洋背景。
**动画**: 战机螺旋桨旋转、子弹火光闪烁。
**打击感与反馈**: 击中敌机产生白色闪光和震屏。
**UI 视觉语言**: 经典街机风格UI。
**音效**: 机枪射击"哒哒哒"声。
**音乐**: 紧张激昂的电子合成器音乐。
**占位策略**: 开发初期使用简单几何形状。
"""

_BAD_PRD = """
## 1. 游戏总览

A game overview.

## 2. 核心游戏循环

Some loop.

## 3. 游戏系统

### Combat System
The combat system synergizes with the progression system.
It directly influences player power and feeds into the economy.
**设计考量**: This ensures good gameplay.

### Skill Tree [INFERRED]
The skill tree complements the combat system and reinforces progression.
**设计考量**: Important design.

## 4. 美术与音效风格

Art style.
"""


# ── Test: QualityReport ─────────────────────────────────────────────────────


def test_quality_report_overall_score():
    report = QualityReport(metrics=[
        QualityMetric(name="a", passed=True, score=1.0),
        QualityMetric(name="b", passed=True, score=0.5),
    ])
    assert report.overall_score == 0.75


def test_quality_report_passed_critical():
    report = QualityReport(metrics=[
        QualityMetric(name="completeness", passed=True, score=1.0),
        QualityMetric(name="banned_phrases", passed=True, score=1.0),
        QualityMetric(name="inferred_accuracy", passed=True, score=1.0),
        QualityMetric(name="length", passed=False, score=0.5),  # non-critical
    ])
    assert report.passed is True


def test_quality_report_fails_on_critical():
    report = QualityReport(metrics=[
        QualityMetric(name="completeness", passed=False, score=0.5),
    ])
    assert report.passed is False


def test_quality_report_failures():
    report = QualityReport(metrics=[
        QualityMetric(name="a", passed=True, score=1.0),
        QualityMetric(name="b", passed=False, score=0.3),
    ])
    assert len(report.failures) == 1
    assert report.failures[0].name == "b"


def test_quality_report_summary():
    report = QualityReport(metrics=[
        QualityMetric(name="test", passed=True, score=1.0, detail="ok"),
    ])
    summary = report.summary()
    assert "PASS" in summary
    assert "test" in summary


# ── Test: Individual Metrics ────────────────────────────────────────────────


def test_completeness_all_sections():
    result = _check_completeness(_GOOD_PRD)
    assert result.passed is True
    assert result.score == 1.0


def test_completeness_missing_section():
    doc = "## 1. 游戏总览\nStuff\n## 2. 核心游戏循环\nMore"
    result = _check_completeness(doc)
    assert result.passed is False
    assert result.score == 0.5


def test_length_passes():
    profile = _COMPLEXITY_PROFILES["arcade"]
    result = _check_length("x" * 4000, profile)
    assert result.passed is True


def test_length_fails():
    profile = _COMPLEXITY_PROFILES["arcade"]
    result = _check_length("x" * 100, profile)
    assert result.passed is False


def test_system_count_exact():
    profile = _COMPLEXITY_PROFILES["arcade"]  # max_systems=4
    result = _check_system_count(_GOOD_PRD, profile)
    assert result.passed is True
    assert result.score == 1.0


def test_system_count_off_by_one():
    profile = {"max_systems": 5}
    result = _check_system_count(_GOOD_PRD, profile)  # has 4 systems
    assert result.passed is True
    assert result.score == 0.8


def test_system_count_missing_section():
    result = _check_system_count("no sections here", {"max_systems": 4})
    assert result.passed is False


def test_inferred_accuracy_no_false_positives():
    core = ["射击系统", "强化道具", "计分系统", "BOSS战斗"]
    result = _check_inferred_accuracy(_GOOD_PRD, core)
    assert result.passed is True
    assert result.score == 1.0


def test_inferred_accuracy_false_positive():
    doc = (
        "## 3. 游戏系统\n"
        "### 射击系统 [INFERRED]\nContent\n"
        "## 4. 美术与音效风格\nArt"
    )
    result = _check_inferred_accuracy(doc, ["射击系统"])
    assert result.passed is False
    assert "false positive" in result.detail.lower()


def test_inferred_accuracy_legitimate_inferred():
    doc = (
        "## 3. 游戏系统\n"
        "### 新手引导系统 [INFERRED]\nContent\n"
        "## 4. 美术与音效风格\nArt"
    )
    result = _check_inferred_accuracy(doc, ["射击系统", "计分系统"])
    assert result.passed is True
    assert "legitimate" in result.detail.lower()


def test_banned_phrases_clean():
    result = _check_banned_phrases(_GOOD_PRD)
    assert result.passed is True


def test_banned_phrases_found():
    result = _check_banned_phrases(_BAD_PRD)
    assert result.passed is False
    assert len([p for p in result.detail.split(",")]) >= 1


def test_faithfulness_arcade_clean():
    result = _check_faithfulness(_GOOD_PRD, "arcade")
    assert result.passed is True


def test_faithfulness_arcade_overdesign():
    doc = "This arcade game has a 技能树 and 装备系统."
    result = _check_faithfulness(doc, "arcade")
    assert result.passed is False


def test_faithfulness_non_arcade_skip():
    doc = "This game has a 技能树 and complex systems."
    result = _check_faithfulness(doc, "mid-core")
    assert result.passed is True
    assert "skip" in result.detail.lower()


def test_specificity_good():
    result = _check_specificity(_GOOD_PRD)
    assert result.passed is True
    assert result.score >= 0.5


def test_specificity_bad():
    result = _check_specificity("A generic description with no details.")
    assert result.passed is False


def test_design_questions_present():
    result = _check_design_questions(_GOOD_PRD)
    assert result.passed is True
    assert result.score == 1.0


def test_design_questions_missing():
    result = _check_design_questions(_BAD_PRD)
    # _BAD_PRD has 设计考量 but without ? marks
    assert result.score < 1.0


# ── Test: Full evaluate() ───────────────────────────────────────────────────


def test_evaluate_good_prd():
    metadata = {
        "complexity": "arcade",
        "core_systems": ["射击系统", "强化道具", "计分系统", "BOSS战斗"],
    }
    report = evaluate(_GOOD_PRD, metadata)
    assert report.overall_score >= 0.7
    assert report.passed is True


def test_evaluate_bad_prd():
    metadata = {
        "complexity": "arcade",
        "core_systems": ["Combat System", "Skill Tree"],
    }
    report = evaluate(_BAD_PRD, metadata)
    assert report.passed is False
    assert len(report.failures) >= 2


# ── Test: Batch evaluation ──────────────────────────────────────────────────


def test_evaluate_batch():
    results = [
        {
            "name": "Game A",
            "prd_document": _GOOD_PRD,
            "metadata": {
                "complexity": "arcade",
                "core_systems": ["射击系统", "强化道具", "计分系统", "BOSS战斗"],
            },
        },
        {
            "name": "Game B",
            "prd_document": _BAD_PRD,
            "metadata": {
                "complexity": "arcade",
                "core_systems": ["Combat System"],
            },
        },
    ]
    reports = evaluate_batch(results)
    assert len(reports) == 2
    assert reports[0][0] == "Game A"
    assert reports[0][1].passed is True
    assert reports[1][0] == "Game B"
    assert reports[1][1].passed is False


def test_batch_summary_format():
    results = [
        {
            "name": "Good",
            "prd_document": _GOOD_PRD,
            "metadata": {
                "complexity": "arcade",
                "core_systems": ["射击系统", "强化道具", "计分系统", "BOSS战斗"],
            },
        },
    ]
    reports = evaluate_batch(results)
    summary = batch_summary(reports)
    assert "1/1 passed" in summary
    assert "Good" in summary
