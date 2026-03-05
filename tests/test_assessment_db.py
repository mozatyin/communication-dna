"""Tests for assessment database operations."""

import pytest

from assessment.database import AssessmentDB


@pytest.fixture
def db(tmp_path):
    """Create a temporary database."""
    db_path = tmp_path / "test.db"
    return AssessmentDB(str(db_path))


def test_create_session(db):
    session_id = db.create_session(
        candidate_name="Alice",
        candidate_email="alice@example.com",
        exam_type="external",
    )
    assert isinstance(session_id, str)
    assert len(session_id) > 0


def test_get_session(db):
    sid = db.create_session("Bob", "bob@example.com", "internal")
    session = db.get_session(sid)
    assert session["candidate_name"] == "Bob"
    assert session["candidate_email"] == "bob@example.com"
    assert session["exam_type"] == "internal"
    assert session["completed_at"] is None


def test_save_answers(db):
    sid = db.create_session("Carol", "carol@example.com", "external")
    db.save_answers(sid, [
        {"question_id": "jt_01", "answer": "C", "score": 2, "dimension": "jumping_thinking"},
        {"question_id": "pdca_01", "answer": "B", "score": 2, "dimension": "pdca_thinking"},
    ])
    answers = db.get_answers(sid)
    assert len(answers) == 2
    assert answers[0]["question_id"] == "jt_01"


def test_save_result(db):
    sid = db.create_session("Dave", "dave@example.com", "external")
    db.save_result(sid, {
        "total_score": 16,
        "passed": True,
        "dimension_scores": {
            "jumping_thinking": 5,
            "pdca_thinking": 4,
            "ai_collaboration": 4,
            "critical_questioning": 3,
        },
        "llm_feedback": "Strong analytical thinking demonstrated.",
    })
    result = db.get_result(sid)
    assert result["total_score"] == 16
    assert result["passed"] is True
    assert result["dimension_scores"]["jumping_thinking"] == 5


def test_get_nonexistent_session(db):
    assert db.get_session("nonexistent") is None


def test_get_nonexistent_result(db):
    sid = db.create_session("Eve", "eve@example.com", "internal")
    assert db.get_result(sid) is None
