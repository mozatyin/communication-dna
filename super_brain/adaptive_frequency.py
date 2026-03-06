"""Adaptive frequency manager for extraction cycles (V2.4).

Each extractor independently adjusts its interval based on extraction yield:
- High yield (>=3 new items): decrease interval (run more often)
- Normal yield (1-2 items): keep current interval
- Zero yield: increase interval (run less often)
"""

from __future__ import annotations


class AdaptiveFrequency:
    """Manages adaptive run frequency for an extractor.

    Parameters
    ----------
    default_interval : int
        Starting interval in turns (default 3).
    min_interval : int
        Minimum interval — never run more often than this (default 2).
    max_interval : int
        Maximum interval — never run less often than this (default 5).
    high_yield_threshold : int
        Number of new items that counts as "high yield" (default 3).
    """

    def __init__(
        self,
        default_interval: int = 3,
        min_interval: int = 2,
        max_interval: int = 5,
        high_yield_threshold: int = 3,
    ) -> None:
        self._interval = default_interval
        self._min = min_interval
        self._max = max_interval
        self._high_threshold = high_yield_threshold
        self._last_run_turn: int = 0

    @property
    def interval(self) -> int:
        return self._interval

    def should_run(self, turn: int) -> bool:
        """Check if the extractor should run at this turn number."""
        if turn - self._last_run_turn >= self._interval:
            self._last_run_turn = turn
            return True
        return False

    def report_yield(self, new_items_count: int) -> None:
        """Report extraction yield to adjust frequency.

        Args:
            new_items_count: Number of new items extracted in the last cycle.
        """
        if new_items_count >= self._high_threshold:
            self._interval = max(self._min, self._interval - 1)
        elif new_items_count == 0:
            self._interval = min(self._max, self._interval + 1)
        # else: normal yield, keep current interval
