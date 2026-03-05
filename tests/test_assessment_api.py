"""Tests for assessment API endpoints."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    """Create test client with temp DB."""
    import assessment.app as app_module
    app_module._db_path = str(tmp_path / "test.db")
    app_module._questions_path = str(Path(__file__).parent.parent / "assessment" / "questions.json")
    app_module._init_services()
    from assessment.app import app
    return TestClient(app)


def test_start_exam(client):
    resp = client.post("/api/exam/start", json={
        "candidate_name": "Alice",
        "candidate_email": "alice@test.com",
        "exam_type": "external",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert len(data["questions"]) == 14


def test_start_exam_missing_fields(client):
    resp = client.post("/api/exam/start", json={"candidate_name": "Alice"})
    assert resp.status_code == 422


def test_submit_and_get_result(client):
    start = client.post("/api/exam/start", json={
        "candidate_name": "Bob",
        "candidate_email": "bob@test.com",
        "exam_type": "internal",
    })
    session_id = start.json()["session_id"]
    questions = start.json()["questions"]

    answers = {}
    for q in questions:
        if q["type"] == "mcq":
            answers[q["id"]] = "A"
        else:
            answers[q["id"]] = "This is my scenario response about the problem."

    mock_score_result = {
        "score": 1.5,
        "dimension_scores": {"pdca_thinking": 0.75, "critical_questioning": 0.75},
        "feedback": "Good analysis.",
    }
    with patch("assessment.app._scorer") as mock_scorer:
        mock_scorer.score.return_value = mock_score_result
        resp = client.post("/api/exam/submit", json={
            "session_id": session_id,
            "answers": answers,
        })

    assert resp.status_code == 200
    data = resp.json()
    assert "total_score" in data
    assert "passed" in data
    assert "dimension_scores" in data


def test_get_result(client):
    start = client.post("/api/exam/start", json={
        "candidate_name": "Carol",
        "candidate_email": "carol@test.com",
        "exam_type": "external",
    })
    session_id = start.json()["session_id"]
    questions = start.json()["questions"]

    answers = {}
    for q in questions:
        if q["type"] == "mcq":
            answers[q["id"]] = "B"
        else:
            answers[q["id"]] = "Detailed scenario response."

    mock_score_result = {
        "score": 1.8,
        "dimension_scores": {"jumping_thinking": 0.9, "ai_collaboration": 0.9},
        "feedback": "Excellent.",
    }
    with patch("assessment.app._scorer") as mock_scorer:
        mock_scorer.score.return_value = mock_score_result
        client.post("/api/exam/submit", json={
            "session_id": session_id,
            "answers": answers,
        })

    resp = client.get(f"/api/exam/result/{session_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_score" in data
    assert "passed" in data


def test_get_result_not_found(client):
    resp = client.get("/api/exam/result/nonexistent")
    assert resp.status_code == 404
