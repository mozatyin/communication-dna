"""Tests for V2.3 ThinkFast rule-based signal detection."""

from super_brain.think_fast import ThinkFast
from super_brain.models import ThinkFastResult


def test_think_fast_detects_new_facts():
    """ThinkFast should detect factual information (job, location, etc.)."""
    conversation = [
        {"role": "chatter", "text": "What do you do for work?"},
        {"role": "speaker", "text": "I'm a software engineer at a startup in San Francisco."},
    ]
    tf = ThinkFast()
    result = tf.analyze(conversation)
    assert isinstance(result, ThinkFastResult)
    assert len(result.new_facts) > 0
    assert any("engineer" in f.lower() or "startup" in f.lower() or "san francisco" in f.lower()
               for f in result.new_facts)


def test_think_fast_detects_opening():
    """ThinkFast should detect unexplored topics hinted at by the speaker."""
    conversation = [
        {"role": "chatter", "text": "What have you been up to lately?"},
        {"role": "speaker", "text": "Just work mostly. I've been thinking about learning guitar though, but haven't started yet."},
    ]
    tf = ThinkFast()
    result = tf.analyze(conversation)
    assert result.opening is not None
    assert "guitar" in result.opening.lower()


def test_think_fast_high_entropy_on_rich_response():
    """A response with lots of new info should have high entropy."""
    conversation = [
        {"role": "chatter", "text": "Tell me about yourself."},
        {"role": "speaker", "text": "I'm 32, work in finance, just moved to Tokyo from London. I love hiking and recently got into pottery. My partner and I are thinking about getting a dog."},
    ]
    tf = ThinkFast()
    result = tf.analyze(conversation)
    assert result.info_entropy >= 0.6


def test_think_fast_low_entropy_on_empty_response():
    """A short, uninformative response should have low entropy."""
    conversation = [
        {"role": "chatter", "text": "What do you think about that?"},
        {"role": "speaker", "text": "Yeah, I guess so."},
    ]
    tf = ThinkFast()
    result = tf.analyze(conversation)
    assert result.info_entropy <= 0.3


def test_think_fast_returns_defaults_on_empty():
    """Empty conversation should return default ThinkFastResult."""
    tf = ThinkFast()
    result = tf.analyze([])
    assert result.new_facts == []
    assert result.opening is None
    assert result.info_entropy == 0.5


def test_think_fast_only_analyzes_last_exchange():
    """ThinkFast should focus on the LAST speaker response, not the whole history."""
    conversation = [
        {"role": "chatter", "text": "What do you do?"},
        {"role": "speaker", "text": "I'm a teacher in Boston."},
        {"role": "chatter", "text": "Nice! Do you enjoy it?"},
        {"role": "speaker", "text": "Yeah, it's fine."},
    ]
    tf = ThinkFast()
    result = tf.analyze(conversation)
    # Should NOT detect "teacher" or "Boston" from the earlier exchange
    # The last exchange "Yeah, it's fine" has no new facts
    assert len(result.new_facts) == 0
    assert result.info_entropy <= 0.3
