"""Tests for V2.4 adaptive frequency manager."""

from super_brain.adaptive_frequency import AdaptiveFrequency


def test_default_interval():
    af = AdaptiveFrequency(default_interval=3)
    assert af.interval == 3


def test_should_run_at_interval():
    af = AdaptiveFrequency(default_interval=3)
    assert af.should_run(turn=3) is True
    assert af.should_run(turn=4) is False
    assert af.should_run(turn=5) is False
    assert af.should_run(turn=6) is True


def test_high_yield_decreases_interval():
    af = AdaptiveFrequency(default_interval=3)
    af.report_yield(3)  # high yield (>=3 new items)
    assert af.interval == 2  # decreased from 3 to 2


def test_zero_yield_increases_interval():
    af = AdaptiveFrequency(default_interval=3)
    af.report_yield(0)  # nothing new
    assert af.interval == 4  # increased from 3 to 4


def test_normal_yield_keeps_interval():
    af = AdaptiveFrequency(default_interval=3)
    af.report_yield(1)  # normal yield
    assert af.interval == 3  # unchanged


def test_interval_clamped_min():
    af = AdaptiveFrequency(default_interval=2, min_interval=2)
    af.report_yield(5)  # high yield
    assert af.interval == 2  # can't go below min


def test_interval_clamped_max():
    af = AdaptiveFrequency(default_interval=5, max_interval=5)
    af.report_yield(0)  # nothing new
    assert af.interval == 5  # can't go above max


def test_repeated_zero_yield_caps_at_max():
    af = AdaptiveFrequency(default_interval=3, max_interval=5)
    for _ in range(10):
        af.report_yield(0)
    assert af.interval == 5


def test_repeated_high_yield_caps_at_min():
    af = AdaptiveFrequency(default_interval=4, min_interval=2)
    for _ in range(10):
        af.report_yield(5)
    assert af.interval == 2


def test_should_run_adapts_to_new_interval():
    af = AdaptiveFrequency(default_interval=3)
    assert af.should_run(turn=3) is True
    af.report_yield(5)  # high yield -> interval becomes 2
    assert af.should_run(turn=4) is False
    assert af.should_run(turn=5) is True  # 3 + 2 = 5
    af.report_yield(0)  # zero yield -> interval becomes 3
    assert af.should_run(turn=8) is True  # 5 + 3 = 8
