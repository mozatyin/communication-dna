"""FastAPI application for the Recursive Thinking Assessment."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from assessment.exam_service import ExamService
from assessment.scenario_scorer import ScenarioScorer

app = FastAPI(title="Recursive Thinking Assessment")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurable paths (overridden in tests)
_db_path: str = os.environ.get("ASSESSMENT_DB", "assessment.db")
_questions_path: str = str(Path(__file__).parent / "questions.json")
_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")

_service: ExamService | None = None
_scorer: ScenarioScorer | None = None


def _init_services() -> None:
    global _service, _scorer
    _service = ExamService(questions_path=_questions_path, db_path=_db_path)
    if _api_key:
        _scorer = ScenarioScorer(api_key=_api_key)


# Initialize on import
_init_services()


# --- Request/Response Models ---

class StartRequest(BaseModel):
    candidate_name: str
    candidate_email: str
    exam_type: str


class SubmitRequest(BaseModel):
    session_id: str
    answers: dict[str, str]


# --- API Endpoints ---

@app.post("/api/exam/start")
def start_exam(req: StartRequest) -> dict[str, Any]:
    assert _service is not None
    return _service.start_exam(req.candidate_name, req.candidate_email, req.exam_type)


@app.post("/api/exam/submit")
def submit_exam(req: SubmitRequest) -> dict[str, Any]:
    assert _service is not None

    session = _service._db.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Separate MCQ and scenario answers
    questions_path = Path(_questions_path)
    with open(questions_path) as f:
        bank = json.load(f)

    mcq_ids = {q["id"] for q in bank["mcq"]}
    scenario_lookup = {q["id"]: q for q in bank["scenarios"]}

    mcq_answers = {qid: ans for qid, ans in req.answers.items() if qid in mcq_ids}
    scenario_answers = {qid: ans for qid, ans in req.answers.items() if qid in scenario_lookup}

    # Score MCQs
    mcq_scores = _service.score_mcq(req.session_id, mcq_answers)

    # Score scenarios via LLM
    scenario_results: list[dict] = []
    for qid, response_text in scenario_answers.items():
        scenario = scenario_lookup.get(qid)
        if not scenario:
            continue
        if _scorer:
            sr = _scorer.score(
                question=scenario["question"],
                rubric=scenario["rubric"],
                response=response_text,
                dimensions=scenario["dimensions"],
                max_score=scenario.get("max_score", 2.0),
            )
        else:
            sr = {"score": 0, "dimension_scores": {}, "feedback": "LLM scoring unavailable."}
        sr["question_id"] = qid
        scenario_results.append(sr)

    # Finalize
    return _service.finalize_result(req.session_id, mcq_scores, scenario_results)


@app.get("/api/exam/result/{session_id}")
def get_result(session_id: str) -> dict[str, Any]:
    assert _service is not None
    result = _service._db.get_result(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    return result


# --- Static Files (frontend) ---

_static_dir = Path(__file__).parent / "static"


@app.get("/")
def index():
    index_file = _static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return HTMLResponse("<h1>Assessment System</h1><p>Frontend not yet built.</p>")


# Mount static files if directory exists
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")
