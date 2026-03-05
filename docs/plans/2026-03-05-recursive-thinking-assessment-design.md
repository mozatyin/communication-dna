# Recursive Thinking Assessment System — Design Document

## Goal

Build a web application that assesses employees and candidates for recursive/PDCA thinking ability, AI collaboration skills, critical questioning, and jumping (abstract-layer) thinking. Two use cases: quick internal employee assessment and 30-minute external recruiting evaluation.

## Core Dimensions

| Dimension | Description |
|-----------|-------------|
| Jumping Thinking | Ability to switch between abstraction layers, connect distant concepts |
| PDCA Experimental Thinking | Iterative hypothesis-test-learn cycles, comfort with ambiguity |
| AI Collaboration | Effective prompting, knowing when to trust/question AI, human-AI workflow |
| Critical Questioning | Identifying assumptions, asking "why", challenging premises |

## Exam Structure

- **12 MCQs**: 3 per dimension, randomly selected from a pool of ~30
- **2 Scenario Questions**: Open-ended, LLM-scored against rubric
- **Time Limit**: 30 minutes
- **Scoring**: 20 points total (MCQ max 16 + scenarios max 4)
- **Pass Threshold**: 14 points (70%)
- **Result**: Pass/fail with per-dimension breakdown

### MCQ Design (1-2 points each)

Each MCQ presents a realistic work situation. Options represent different thinking approaches:
- 2 pts: Demonstrates the target dimension strongly
- 1 pt: Partially demonstrates it
- 0 pts: Shows rigid/surface-level thinking

### Scenario Design (2 points each)

Candidate writes 200-400 word response to an open-ended problem. LLM scores against a 4-criterion rubric:
- Dimension relevance (0-0.5)
- Depth of reasoning (0-0.5)
- Practical applicability (0-0.5)
- Originality/insight (0-0.5)

## Sample Questions

### Jumping Thinking MCQ
> Your team's recommendation engine has low engagement. You notice the company cafeteria recently changed its menu layout and saw a 40% increase in selections. What do you do?
>
> A) Ignore it — cafeteria has nothing to do with tech (0 pts)
> B) Note it's interesting but focus on A/B testing the algorithm (1 pt)
> C) Study the cafeteria's choice architecture principles and prototype applying them to the recommendation UI (2 pts)

### PDCA Experimental Thinking MCQ
> You have a theory that shorter onboarding flows increase retention. Your manager wants a full analysis before any changes. What do you do?
>
> A) Write the full analysis report as requested (0 pts)
> B) Propose a small A/B test on 5% of users while writing the analysis (2 pts)
> C) Wait for more data before doing anything (0 pts)

### AI Collaboration MCQ
> You ask an AI to generate a database schema. The output looks reasonable but you notice it denormalized a table you'd normally normalize. What do you do?
>
> A) Accept it — AI knows best practices (0 pts)
> B) Ask the AI why it chose denormalization, evaluate its reasoning, then decide (2 pts)
> C) Reject it and write your own schema from scratch (1 pt)

### Critical Questioning MCQ
> Your team's dashboard shows a 15% improvement in user satisfaction after a redesign. Leadership is celebrating. What's your reaction?
>
> A) Celebrate with the team (0 pts)
> B) Ask what the baseline was, how satisfaction was measured, and whether the sample was representative (2 pts)
> C) Suggest running the test longer (1 pt)

### Scenario Question Example
> Your company's customer support AI chatbot resolves 80% of tickets automatically, but customer satisfaction scores have dropped 12% since launch. Leadership wants to add more training data to improve the chatbot.
>
> Describe how you would approach this problem. Consider: what assumptions might be wrong, what experiments you'd run, and how you'd decide between improving the chatbot vs. changing the approach entirely.

**LLM Scoring Rubric**: Does the response question the 80% resolution metric? Does it propose small experiments? Does it consider the chatbot might be solving the wrong problem? Does it connect to broader patterns?

## Technical Architecture

### Frontend
Single-page app (vanilla HTML/CSS/JS). Three views:
- **Start page**: Name, email, exam type selection
- **Exam page**: One question at a time, timer, answer collection
- **Result page**: Pass/fail with dimension radar chart

### Backend
FastAPI (Python), aligned with existing project stack.

**Endpoints**:
- `POST /api/exam/start` — create session, return question set
- `POST /api/exam/submit` — receive answers, trigger scoring
- `GET /api/exam/result/{session_id}` — return scored result

### Scoring Pipeline
- **MCQ**: Deterministic. Each option has pre-assigned score.
- **Scenarios**: LLM scoring via Anthropic API. Prompt = rubric + response → structured score JSON.

### Data Model (SQLite)
```
exams:     id, type(internal|external), created_at
sessions:  id, exam_id, candidate_name, candidate_email, started_at, completed_at
answers:   id, session_id, question_id, answer_text, score, dimension
results:   id, session_id, total_score, passed, dimension_scores(JSON), llm_feedback
```

### Question Bank
JSON file (`questions.json`) with ~30 MCQs + ~6 scenarios. Exam randomly selects from pool.

### Key Decisions
- No user auth — exam links are one-time use per session
- No admin panel in v1 — questions managed via JSON
- LLM scoring is async — result page polls until complete
- Single Python package, deployable with `uvicorn`

## Dependencies
- `fastapi`, `uvicorn` — web framework
- `anthropic` — LLM scoring (already in project)
- `sqlite3` — built-in, no extra dependency
- `jinja2` — HTML templating (optional, can use static files)
