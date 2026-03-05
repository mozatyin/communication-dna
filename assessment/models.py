"""Data models for the assessment system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MCQuestion:
    """A multiple-choice question."""
    id: str
    dimension: str
    question: str
    options: list[dict[str, Any]]  # [{label, text, score}]


@dataclass
class ScenarioQuestion:
    """An open-ended scenario question."""
    id: str
    dimensions: list[str]
    question: str
    rubric: dict[str, str]
    max_score: float


@dataclass
class ExamSession:
    """An exam session for a candidate."""
    session_id: str
    candidate_name: str
    candidate_email: str
    exam_type: str  # "internal" | "external"
    mcq_ids: list[str] = field(default_factory=list)
    scenario_ids: list[str] = field(default_factory=list)


@dataclass
class ExamResult:
    """Scored result of an exam."""
    total_score: float
    passed: bool
    dimension_scores: dict[str, float]
    llm_feedback: str = ""
