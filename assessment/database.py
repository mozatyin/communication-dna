"""SQLite database for assessment sessions and results."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any


class AssessmentDB:
    """Simple SQLite wrapper for assessment data."""

    def __init__(self, db_path: str = "assessment.db"):
        self._db_path = db_path
        self._init_tables()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    candidate_name TEXT NOT NULL,
                    candidate_email TEXT NOT NULL,
                    exam_type TEXT NOT NULL,
                    question_ids TEXT NOT NULL DEFAULT '[]',
                    started_at TEXT NOT NULL,
                    completed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS answers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    question_id TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    score REAL,
                    dimension TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );
                CREATE TABLE IF NOT EXISTS results (
                    session_id TEXT PRIMARY KEY,
                    total_score REAL NOT NULL,
                    passed INTEGER NOT NULL,
                    dimension_scores TEXT NOT NULL,
                    llm_feedback TEXT DEFAULT '',
                    scored_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
                );
            """)

    def create_session(
        self, candidate_name: str, candidate_email: str, exam_type: str
    ) -> str:
        session_id = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, candidate_name, candidate_email, exam_type, started_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, candidate_name, candidate_email, exam_type, now),
            )
        return session_id

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        if not row:
            return None
        return dict(row)

    def save_answers(self, session_id: str, answers: list[dict]) -> None:
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO answers (session_id, question_id, answer, score, dimension) VALUES (?, ?, ?, ?, ?)",
                [(session_id, a["question_id"], a["answer"], a.get("score"), a["dimension"]) for a in answers],
            )
            conn.execute(
                "UPDATE sessions SET completed_at = ? WHERE session_id = ?",
                (datetime.now(timezone.utc).isoformat(), session_id),
            )

    def get_answers(self, session_id: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM answers WHERE session_id = ? ORDER BY id", (session_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def save_result(self, session_id: str, result: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO results (session_id, total_score, passed, dimension_scores, llm_feedback, scored_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    result["total_score"],
                    1 if result["passed"] else 0,
                    json.dumps(result["dimension_scores"]),
                    result.get("llm_feedback", ""),
                    now,
                ),
            )

    def get_result(self, session_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM results WHERE session_id = ?", (session_id,)
            ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["dimension_scores"] = json.loads(result["dimension_scores"])
        result["passed"] = bool(result["passed"])
        return result
