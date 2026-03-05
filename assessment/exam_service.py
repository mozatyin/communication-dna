"""Exam service — question selection, MCQ scoring, result assembly."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from assessment.database import AssessmentDB

_DIMENSIONS = ["jumping_thinking", "pdca_thinking", "ai_collaboration", "critical_questioning"]
_MCQ_PER_DIM = 3
_SCENARIOS_COUNT = 2
_PASS_THRESHOLD = 14  # out of 20


class ExamService:
    """Handles exam lifecycle: start, score MCQ, assemble results."""

    def __init__(self, questions_path: str | None = None, db_path: str = "assessment.db"):
        if questions_path is None:
            questions_path = str(Path(__file__).parent / "questions.json")
        with open(questions_path) as f:
            bank = json.load(f)
        self._mcq_bank: list[dict] = bank["mcq"]
        self._scenario_bank: list[dict] = bank["scenarios"]
        self._db = AssessmentDB(db_path)

        # Index MCQs by dimension
        self._mcq_by_dim: dict[str, list[dict]] = {d: [] for d in _DIMENSIONS}
        for q in self._mcq_bank:
            dim = q["dimension"]
            if dim in self._mcq_by_dim:
                self._mcq_by_dim[dim].append(q)

    def start_exam(self, name: str, email: str, exam_type: str) -> dict[str, Any]:
        """Create a new exam session and select questions.

        Returns dict with session_id and questions (scores stripped from MCQ options).
        """
        session_id = self._db.create_session(name, email, exam_type)

        # Select MCQs: 3 per dimension
        selected_mcqs: list[dict] = []
        for dim in _DIMENSIONS:
            pool = self._mcq_by_dim[dim]
            picked = random.sample(pool, min(_MCQ_PER_DIM, len(pool)))
            selected_mcqs.extend(picked)

        # Select scenarios
        selected_scenarios = random.sample(
            self._scenario_bank, min(_SCENARIOS_COUNT, len(self._scenario_bank))
        )

        # Build questions for frontend (strip scores from MCQ options)
        questions: list[dict] = []
        for q in selected_mcqs:
            questions.append({
                "id": q["id"],
                "type": "mcq",
                "dimension": q["dimension"],
                "question": q["question"],
                "options": [{"label": o["label"], "text": o["text"]} for o in q["options"]],
            })
        for q in selected_scenarios:
            questions.append({
                "id": q["id"],
                "type": "scenario",
                "dimensions": q["dimensions"],
                "question": q["question"],
                "max_words": 400,
            })

        return {"session_id": session_id, "questions": questions}

    def score_mcq(self, session_id: str, answers: dict[str, str]) -> dict[str, Any]:
        """Score MCQ answers deterministically.

        Args:
            session_id: The exam session ID.
            answers: {question_id: selected_label} e.g. {"jt_01": "C"}

        Returns:
            Dict with mcq_total and per-dimension scores.
        """
        # Build lookup: question_id -> {label -> score}
        score_lookup: dict[str, dict[str, int]] = {}
        dim_lookup: dict[str, str] = {}
        for q in self._mcq_bank:
            score_lookup[q["id"]] = {o["label"]: o["score"] for o in q["options"]}
            dim_lookup[q["id"]] = q["dimension"]

        dimension_scores: dict[str, float] = {d: 0 for d in _DIMENSIONS}
        answer_records: list[dict] = []
        total = 0

        for qid, label in answers.items():
            if qid not in score_lookup:
                continue
            score = score_lookup[qid].get(label, 0)
            dim = dim_lookup[qid]
            dimension_scores[dim] += score
            total += score
            answer_records.append({
                "question_id": qid,
                "answer": label,
                "score": score,
                "dimension": dim,
            })

        self._db.save_answers(session_id, answer_records)
        return {"mcq_total": total, "dimension_scores": dimension_scores}

    def finalize_result(
        self,
        session_id: str,
        mcq_scores: dict[str, Any],
        scenario_scores: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Combine MCQ and scenario scores into final result.

        Args:
            session_id: The exam session ID.
            mcq_scores: Output from score_mcq().
            scenario_scores: List of {question_id, score, dimension_scores, feedback}.

        Returns:
            Final result dict with total_score, passed, dimension breakdown.
        """
        dimension_totals = dict(mcq_scores["dimension_scores"])
        scenario_total = 0
        feedback_parts: list[str] = []

        for ss in scenario_scores:
            scenario_total += ss.get("score", 0)
            for dim, val in ss.get("dimension_scores", {}).items():
                dimension_totals[dim] = dimension_totals.get(dim, 0) + val
            if ss.get("feedback"):
                feedback_parts.append(ss["feedback"])

        total = mcq_scores["mcq_total"] + scenario_total
        passed = total >= _PASS_THRESHOLD

        result = {
            "total_score": total,
            "passed": passed,
            "dimension_scores": dimension_totals,
            "llm_feedback": "\n\n".join(feedback_parts),
        }
        self._db.save_result(session_id, result)
        return result
