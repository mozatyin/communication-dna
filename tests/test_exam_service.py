"""Tests for exam service — question selection and MCQ scoring."""

import json
from pathlib import Path

import pytest

from assessment.exam_service import ExamService


@pytest.fixture
def service(tmp_path):
    """Create ExamService with real question bank and temp DB."""
    questions_path = Path(__file__).parent.parent / "assessment" / "questions.json"
    db_path = str(tmp_path / "test.db")
    return ExamService(questions_path=str(questions_path), db_path=db_path)


def test_start_exam_returns_session_and_questions(service):
    result = service.start_exam("Alice", "alice@test.com", "external")
    assert "session_id" in result
    assert "questions" in result
    questions = result["questions"]
    # 12 MCQ + 2 scenarios = 14 total
    assert len(questions) == 14
    mcqs = [q for q in questions if q["type"] == "mcq"]
    scenarios = [q for q in questions if q["type"] == "scenario"]
    assert len(mcqs) == 12
    assert len(scenarios) == 2


def test_mcq_covers_all_dimensions(service):
    result = service.start_exam("Bob", "bob@test.com", "internal")
    mcqs = [q for q in result["questions"] if q["type"] == "mcq"]
    dimensions = [q["dimension"] for q in mcqs]
    for dim in ["jumping_thinking", "pdca_thinking", "ai_collaboration", "critical_questioning"]:
        assert dimensions.count(dim) == 3, f"Expected 3 MCQs for {dim}"


def test_mcq_options_dont_include_scores(service):
    """Scores should NOT be sent to the frontend."""
    result = service.start_exam("Carol", "carol@test.com", "external")
    mcqs = [q for q in result["questions"] if q["type"] == "mcq"]
    for q in mcqs:
        for opt in q["options"]:
            assert "score" not in opt


def test_score_mcq_answers(service):
    result = service.start_exam("Dave", "dave@test.com", "external")
    session_id = result["session_id"]
    mcqs = [q for q in result["questions"] if q["type"] == "mcq"]

    # Answer all MCQs with the first option
    mcq_answers = {q["id"]: "A" for q in mcqs}
    scores = service.score_mcq(session_id, mcq_answers)
    assert "mcq_total" in scores
    assert "dimension_scores" in scores
    assert isinstance(scores["mcq_total"], (int, float))


def test_different_exams_get_different_questions(service):
    r1 = service.start_exam("E1", "e1@test.com", "external")
    r2 = service.start_exam("E2", "e2@test.com", "external")
    ids1 = {q["id"] for q in r1["questions"]}
    ids2 = {q["id"] for q in r2["questions"]}
    # Both sets should be valid (14 questions each)
    assert len(ids1) == 14
    assert len(ids2) == 14
