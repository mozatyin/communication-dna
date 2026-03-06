"""Soul Coverage scoring for V2.4 evaluation.

Measures how populated the Soul model is after a conversation.
Components (V2.4 — facts + reality + secrets):
- facts: min(count / 10, 1.0)
- reality: 1.0 if populated, else 0.0
- secrets: min(count / 3, 1.0)
"""

from __future__ import annotations

from super_brain.models import Soul


def compute_soul_coverage(soul: Soul) -> float:
    """Compute Soul Coverage score (0.0-1.0).

    V2.4 components (3 items, equally weighted):
    - facts: min(len / 10, 1.0) — 10+ facts = full
    - reality: 1.0 if populated, else 0.0
    - secrets: min(len / 3, 1.0) — 3+ secrets = full

    Returns:
        Float between 0.0 and 1.0.
    """
    scores: list[float] = []
    scores.append(min(len(soul.facts) / 10.0, 1.0))
    scores.append(1.0 if soul.reality else 0.0)
    scores.append(min(len(soul.secrets) / 3.0, 1.0))
    return sum(scores) / len(scores) if scores else 0.0
