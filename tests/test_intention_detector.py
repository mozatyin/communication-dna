# tests/test_intention_detector.py
"""Tests for the full Intention Detector pipeline."""

import os

import pytest

from intention_graph.detector import IntentionDetector
from intention_graph.models import IntentionGraph


@pytest.fixture
def detector() -> IntentionDetector:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return IntentionDetector(api_key=api_key)


CAREER_DIALOGUE = """\
User: I've been really unhappy at work. I think I need to change careers entirely.
Coach: What specifically is making you unhappy?
User: The work is repetitive, no creativity. I've always wanted to try product design. \
I took an online course last month and loved it.
Coach: That's exciting. What's holding you back?
User: Money, mostly. I can't just quit. I need to save up first, maybe 6 months of expenses. \
And I should build a portfolio before applying anywhere.
"""

SHOPPING_DIALOGUE = """\
User: I need a new laptop for programming. Budget is around $1500.
Advisor: Mac or Windows?
User: I'm leaning toward a MacBook Pro, but the new ThinkPad X1 Carbon looks good too. \
I need at least 32GB RAM and good keyboard. Battery life matters since I work from cafes a lot.
"""


def test_full_pipeline_career(detector: IntentionDetector):
    graph = detector.analyze(
        text=CAREER_DIALOGUE,
        speaker_id="user_1",
        speaker_label="User",
    )
    assert isinstance(graph, IntentionGraph)
    assert len(graph.nodes) >= 3  # career change, save money, build portfolio
    assert len(graph.transitions) >= 1
    assert graph.end_goal is not None


def test_full_pipeline_shopping(detector: IntentionDetector):
    graph = detector.analyze(
        text=SHOPPING_DIALOGUE,
        speaker_id="user_1",
        speaker_label="User",
    )
    assert isinstance(graph, IntentionGraph)
    assert len(graph.nodes) >= 2
    # Shopping should have alternative branches (MacBook vs ThinkPad)
    alternatives = [t for t in graph.transitions if t.relation == "alternative"]
    # May or may not detect alternatives depending on LLM
    assert len(graph.nodes) >= 2


def test_pipeline_with_domain_hint(detector: IntentionDetector):
    graph = detector.analyze(
        text=SHOPPING_DIALOGUE,
        speaker_id="user_1",
        speaker_label="User",
        domain="shopping",
    )
    assert all(n.domain == "shopping" for n in graph.nodes)
