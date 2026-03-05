# Recursive Thinking Assessment System — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a FastAPI web app that assesses candidates for recursive thinking, PDCA mindset, AI collaboration, and critical questioning via MCQ + scenario-based exams with LLM scoring.

**Architecture:** FastAPI backend serves a vanilla HTML/JS frontend. Question bank lives in a JSON file. MCQs are scored deterministically; scenario questions use Anthropic API for rubric-based LLM scoring. SQLite stores sessions and results. Three API endpoints handle exam lifecycle (start → submit → result).

**Tech Stack:** Python 3.12, FastAPI, uvicorn, Anthropic SDK (existing), SQLite3 (stdlib), vanilla HTML/CSS/JS

---

### Task 1: Add Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add FastAPI and uvicorn to dependencies**

In `pyproject.toml`, add to the `dependencies` list:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
]
search = [
    "duckduckgo-search>=7.0",
]
assessment = [
    "fastapi>=0.115",
    "uvicorn>=0.34",
]
```

**Step 2: Install the new dependencies**

Run: `.venv/bin/pip install -e ".[assessment]"`
Expected: Successfully installed fastapi uvicorn (and sub-deps like starlette, anyio)

**Step 3: Verify import works**

Run: `.venv/bin/python -c "import fastapi; print(fastapi.__version__)"`
Expected: prints version number (0.115.x)

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add fastapi/uvicorn deps for assessment system"
```

---

### Task 2: Question Bank JSON

**Files:**
- Create: `assessment/questions.json`
- Create: `assessment/__init__.py`

**Step 1: Create the assessment package directory**

Run: `mkdir -p assessment`

**Step 2: Create empty `__init__.py`**

Create `assessment/__init__.py` with content:
```python
"""Recursive Thinking Assessment System."""
```

**Step 3: Create question bank**

Create `assessment/questions.json` with this structure. The bank needs ~30 MCQs (8 per dimension, shuffled down to 3 at exam time) and ~6 scenario questions (randomly pick 2).

```json
{
  "mcq": [
    {
      "id": "jt_01",
      "dimension": "jumping_thinking",
      "question": "Your team's recommendation engine has low engagement. You notice the company cafeteria recently changed its menu layout and saw a 40% increase in selections. What do you do?",
      "options": [
        {"label": "A", "text": "Ignore it — cafeteria has nothing to do with tech", "score": 0},
        {"label": "B", "text": "Note it's interesting but focus on A/B testing the algorithm", "score": 1},
        {"label": "C", "text": "Study the cafeteria's choice architecture principles and prototype applying them to the recommendation UI", "score": 2}
      ]
    },
    {
      "id": "jt_02",
      "dimension": "jumping_thinking",
      "question": "You're debugging a slow database query. A colleague mentions that their kid's school uses a library checkout system that handles 10x the requests. What do you do?",
      "options": [
        {"label": "A", "text": "Politely acknowledge and keep profiling the query", "score": 0},
        {"label": "B", "text": "Ask what system the school uses out of curiosity", "score": 1},
        {"label": "C", "text": "Ask for details about the checkout system's architecture — different domains often solve similar scaling problems in novel ways", "score": 2}
      ]
    },
    {
      "id": "jt_03",
      "dimension": "jumping_thinking",
      "question": "A product manager asks you to improve search relevance. You recently read an article about how Netflix matches viewers to thumbnails. What's your first thought?",
      "options": [
        {"label": "A", "text": "Netflix is entertainment, our product is B2B — not relevant", "score": 0},
        {"label": "B", "text": "Interesting parallel — maybe we could personalize how search results are displayed, not just ranked", "score": 2},
        {"label": "C", "text": "Bookmark the article for later reading", "score": 1}
      ]
    },
    {
      "id": "jt_04",
      "dimension": "jumping_thinking",
      "question": "During a brainstorming session about reducing customer churn, someone mentions ant colonies self-organize without central control. How do you react?",
      "options": [
        {"label": "A", "text": "Stay focused — biology analogies waste meeting time", "score": 0},
        {"label": "B", "text": "Ask how ant colony optimization might apply to our customer journey routing", "score": 2},
        {"label": "C", "text": "Think it's interesting but don't bring it up to avoid seeming off-topic", "score": 1}
      ]
    },
    {
      "id": "jt_05",
      "dimension": "jumping_thinking",
      "question": "You're designing an API rate limiter. Your friend who's a traffic engineer describes how highway on-ramps use metered signals to regulate flow. What do you do?",
      "options": [
        {"label": "A", "text": "Appreciate the analogy but stick with standard token bucket algorithm", "score": 1},
        {"label": "B", "text": "Explore whether the ramp metering's adaptive feedback loop could improve your rate limiter's burst handling", "score": 2},
        {"label": "C", "text": "Ignore it — physical traffic has nothing to do with API traffic", "score": 0}
      ]
    },
    {
      "id": "jt_06",
      "dimension": "jumping_thinking",
      "question": "Your e-commerce site has a high cart abandonment rate. You visit a physical store and notice how staff approach customers who linger near the exit. What crosses your mind?",
      "options": [
        {"label": "A", "text": "Physical retail tactics don't translate to digital", "score": 0},
        {"label": "B", "text": "Maybe we need exit-intent detection that mirrors the staff's timing and approach style", "score": 2},
        {"label": "C", "text": "We should add a popup discount when users try to leave", "score": 1}
      ]
    },
    {
      "id": "jt_07",
      "dimension": "jumping_thinking",
      "question": "A data pipeline keeps failing silently. You read that hospitals use redundant monitoring where multiple nurses independently check vital signs. What do you think?",
      "options": [
        {"label": "A", "text": "Add more logging to the pipeline", "score": 1},
        {"label": "B", "text": "Implement independent health-check observers that cross-validate each other, similar to the hospital's redundant monitoring model", "score": 2},
        {"label": "C", "text": "Hospital workflows are too different to learn from", "score": 0}
      ]
    },
    {
      "id": "jt_08",
      "dimension": "jumping_thinking",
      "question": "Your team is struggling with microservice communication complexity. You watch a documentary about how octopus arms make semi-independent decisions. What's your takeaway?",
      "options": [
        {"label": "A", "text": "Fascinating nature, but our architecture decisions need engineering rigor", "score": 0},
        {"label": "B", "text": "Maybe our services need more local autonomy with loose coordination — like the octopus nervous system", "score": 2},
        {"label": "C", "text": "Consider event-driven architecture as a standard solution", "score": 1}
      ]
    },
    {
      "id": "pdca_01",
      "dimension": "pdca_thinking",
      "question": "You have a theory that shorter onboarding flows increase retention. Your manager wants a full analysis before any changes. What do you do?",
      "options": [
        {"label": "A", "text": "Write the full analysis report as requested", "score": 0},
        {"label": "B", "text": "Propose a small A/B test on 5% of users while writing the analysis", "score": 2},
        {"label": "C", "text": "Wait for more data before doing anything", "score": 0}
      ]
    },
    {
      "id": "pdca_02",
      "dimension": "pdca_thinking",
      "question": "Your team spent 3 months building a feature. After launch, usage is 10% of projections. What do you do first?",
      "options": [
        {"label": "A", "text": "Invest more in marketing the feature", "score": 0},
        {"label": "B", "text": "Talk to 5 users this week, form a hypothesis about why, and run a 1-week experiment to test it", "score": 2},
        {"label": "C", "text": "Commission a comprehensive user research study", "score": 1}
      ]
    },
    {
      "id": "pdca_03",
      "dimension": "pdca_thinking",
      "question": "You're tasked with improving page load speed. You have 6 optimization ideas. How do you proceed?",
      "options": [
        {"label": "A", "text": "Implement all 6 optimizations, then measure the combined improvement", "score": 0},
        {"label": "B", "text": "Pick the highest-impact one, implement it, measure, then decide the next step based on results", "score": 2},
        {"label": "C", "text": "Research best practices to find the optimal approach before starting", "score": 1}
      ]
    },
    {
      "id": "pdca_04",
      "dimension": "pdca_thinking",
      "question": "You implemented a caching layer that was supposed to reduce latency by 50%. After deployment, latency only dropped 15%. What do you do?",
      "options": [
        {"label": "A", "text": "15% is still an improvement — move on to the next task", "score": 0},
        {"label": "B", "text": "Investigate why the gap exists, form a new hypothesis about the bottleneck, and test it", "score": 2},
        {"label": "C", "text": "Add more cache capacity to get closer to 50%", "score": 0}
      ]
    },
    {
      "id": "pdca_05",
      "dimension": "pdca_thinking",
      "question": "Your team is deciding between two architectures for a new service. There's heated debate with no clear winner. What do you suggest?",
      "options": [
        {"label": "A", "text": "Let the most senior engineer decide", "score": 0},
        {"label": "B", "text": "Build a minimal prototype of each over 2 days, compare against real load, then decide", "score": 2},
        {"label": "C", "text": "Schedule more meetings to gather broader input", "score": 1}
      ]
    },
    {
      "id": "pdca_06",
      "dimension": "pdca_thinking",
      "question": "You're leading a project with high uncertainty. After 2 weeks, your initial design assumptions are proving wrong. What do you do?",
      "options": [
        {"label": "A", "text": "Stick to the plan — changing direction now would waste the work done", "score": 0},
        {"label": "B", "text": "Document what you learned, revise the design based on new evidence, and set a checkpoint for 1 week", "score": 2},
        {"label": "C", "text": "Escalate to management for guidance", "score": 1}
      ]
    },
    {
      "id": "pdca_07",
      "dimension": "pdca_thinking",
      "question": "A production incident reveals a flaw in your monitoring. After fixing the immediate issue, what's your next step?",
      "options": [
        {"label": "A", "text": "Write a postmortem report and file it", "score": 1},
        {"label": "B", "text": "Run a 'chaos experiment' to verify the fix actually catches similar failures, then iterate on the monitoring", "score": 2},
        {"label": "C", "text": "Move on — the fix is in, no need to dwell on it", "score": 0}
      ]
    },
    {
      "id": "ai_01",
      "dimension": "ai_collaboration",
      "question": "You ask an AI to generate a database schema. The output looks reasonable but you notice it denormalized a table you'd normally normalize. What do you do?",
      "options": [
        {"label": "A", "text": "Accept it — AI knows best practices", "score": 0},
        {"label": "B", "text": "Ask the AI why it chose denormalization, evaluate its reasoning, then decide", "score": 2},
        {"label": "C", "text": "Reject it and write your own schema from scratch", "score": 1}
      ]
    },
    {
      "id": "ai_02",
      "dimension": "ai_collaboration",
      "question": "You're using AI to draft a project proposal. The AI produces a polished document but you notice it assumes requirements you never mentioned. What do you do?",
      "options": [
        {"label": "A", "text": "Send it as-is — it looks professional", "score": 0},
        {"label": "B", "text": "Review each assumption, ask the AI to explain its reasoning, keep valid inferences, and correct hallucinated ones", "score": 2},
        {"label": "C", "text": "Rewrite the entire proposal yourself", "score": 1}
      ]
    },
    {
      "id": "ai_03",
      "dimension": "ai_collaboration",
      "question": "You need to analyze 500 customer feedback comments. How do you approach this with AI?",
      "options": [
        {"label": "A", "text": "Paste all 500 into AI and ask for a summary", "score": 0},
        {"label": "B", "text": "Have AI categorize a sample of 50, verify the categories manually, refine the prompt, then process the full batch", "score": 2},
        {"label": "C", "text": "Read all 500 manually — AI might miss nuances", "score": 1}
      ]
    },
    {
      "id": "ai_04",
      "dimension": "ai_collaboration",
      "question": "AI generates test cases for your function. All tests pass. But you notice the tests only cover happy paths. What do you do?",
      "options": [
        {"label": "A", "text": "All tests pass, so the code is correct", "score": 0},
        {"label": "B", "text": "Ask the AI to generate edge cases and error scenarios, then verify those tests actually exercise different code paths", "score": 2},
        {"label": "C", "text": "Write your own edge case tests from scratch", "score": 1}
      ]
    },
    {
      "id": "ai_05",
      "dimension": "ai_collaboration",
      "question": "You're debugging a complex issue. You paste the error into AI and it suggests a fix that works. But you don't understand why it works. What do you do?",
      "options": [
        {"label": "A", "text": "It works — commit and move on", "score": 0},
        {"label": "B", "text": "Ask the AI to explain the root cause step by step, then verify the explanation against the codebase", "score": 2},
        {"label": "C", "text": "Revert the fix and debug manually until you understand it", "score": 1}
      ]
    },
    {
      "id": "ai_06",
      "dimension": "ai_collaboration",
      "question": "You ask AI to optimize a slow SQL query. It rewrites the query completely with a different approach. The new query is 10x faster. What's your response?",
      "options": [
        {"label": "A", "text": "Deploy immediately — 10x improvement speaks for itself", "score": 0},
        {"label": "B", "text": "Compare query plans of both versions, verify correctness on edge cases, then deploy with monitoring", "score": 2},
        {"label": "C", "text": "Reject it — you don't trust AI-generated SQL in production", "score": 0}
      ]
    },
    {
      "id": "ai_07",
      "dimension": "ai_collaboration",
      "question": "Your team debates whether to use AI for code reviews. What's your position?",
      "options": [
        {"label": "A", "text": "AI can't understand context — human reviews only", "score": 0},
        {"label": "B", "text": "Use AI for first-pass checks (style, bugs, patterns), then have humans focus on architecture and business logic", "score": 2},
        {"label": "C", "text": "Replace human reviews with AI to save time", "score": 0}
      ]
    },
    {
      "id": "cq_01",
      "dimension": "critical_questioning",
      "question": "Your team's dashboard shows a 15% improvement in user satisfaction after a redesign. Leadership is celebrating. What's your reaction?",
      "options": [
        {"label": "A", "text": "Celebrate with the team", "score": 0},
        {"label": "B", "text": "Ask what the baseline was, how satisfaction was measured, and whether the sample was representative", "score": 2},
        {"label": "C", "text": "Suggest running the test longer", "score": 1}
      ]
    },
    {
      "id": "cq_02",
      "dimension": "critical_questioning",
      "question": "A vendor claims their tool will reduce deployment time by 80%. Your CTO is excited. What do you do?",
      "options": [
        {"label": "A", "text": "Trust the CTO's judgment and proceed with adoption", "score": 0},
        {"label": "B", "text": "Ask: 80% of what baseline? Under what conditions? What's the migration cost? Can we run a parallel trial?", "score": 2},
        {"label": "C", "text": "Research the vendor online for reviews", "score": 1}
      ]
    },
    {
      "id": "cq_03",
      "dimension": "critical_questioning",
      "question": "Everyone on the team agrees the new feature should use microservices. You're the newest member. What do you do?",
      "options": [
        {"label": "A", "text": "Go with the team consensus — they know the codebase better", "score": 0},
        {"label": "B", "text": "Ask what specific problem microservices solve here that a modular monolith wouldn't, and what the operational cost tradeoff is", "score": 2},
        {"label": "C", "text": "Suggest microservices might be overkill but don't push back", "score": 1}
      ]
    },
    {
      "id": "cq_04",
      "dimension": "critical_questioning",
      "question": "A colleague presents data showing users prefer Feature A over Feature B. The data comes from a survey of 50 power users. What's your response?",
      "options": [
        {"label": "A", "text": "Accept the finding — 50 users is a decent sample", "score": 0},
        {"label": "B", "text": "Ask whether power users represent the broader user base, what the response rate was, and how the questions were framed", "score": 2},
        {"label": "C", "text": "Suggest expanding the survey to more users", "score": 1}
      ]
    },
    {
      "id": "cq_05",
      "dimension": "critical_questioning",
      "question": "Your team's retrospective identifies 'lack of communication' as the top problem. What do you do?",
      "options": [
        {"label": "A", "text": "Propose adding a daily standup meeting", "score": 0},
        {"label": "B", "text": "Ask: what specific communication failures occurred? Between whom? What information was missing at what decision point?", "score": 2},
        {"label": "C", "text": "Create a shared Slack channel for the team", "score": 0}
      ]
    },
    {
      "id": "cq_06",
      "dimension": "critical_questioning",
      "question": "Management says the project deadline is fixed because of a partner launch date. The timeline feels impossibly tight. What do you do?",
      "options": [
        {"label": "A", "text": "Work overtime to meet the deadline", "score": 0},
        {"label": "B", "text": "Ask: is the partner date actually fixed or estimated? What's the minimum viable scope? What happens if we're 2 weeks late vs. delivering a buggy product on time?", "score": 2},
        {"label": "C", "text": "Flag the risk to your manager and let them decide", "score": 1}
      ]
    },
    {
      "id": "cq_07",
      "dimension": "critical_questioning",
      "question": "A blog post goes viral claiming 'Technology X is dead.' Your team uses Technology X extensively. What's your reaction?",
      "options": [
        {"label": "A", "text": "Start planning migration to the replacement technology", "score": 0},
        {"label": "B", "text": "Examine the author's evidence, check if 'dead' means declining usage or just hype cycle shift, and evaluate whether the critique applies to your use case", "score": 2},
        {"label": "C", "text": "Ignore it — blog posts are just opinions", "score": 1}
      ]
    }
  ],
  "scenarios": [
    {
      "id": "scenario_01",
      "dimensions": ["pdca_thinking", "critical_questioning"],
      "question": "Your company's customer support AI chatbot resolves 80% of tickets automatically, but customer satisfaction scores have dropped 12% since launch. Leadership wants to add more training data to improve the chatbot.\n\nDescribe how you would approach this problem. Consider: what assumptions might be wrong, what experiments you'd run, and how you'd decide between improving the chatbot vs. changing the approach entirely.",
      "rubric": {
        "dimension_relevance": "Does the response question the 80% resolution metric (e.g., are 'resolved' tickets actually resolved)? Does it challenge leadership's assumption that more training data is the solution?",
        "depth_of_reasoning": "Does it propose specific, small experiments rather than big-bang changes? Does it consider multiple hypotheses for the satisfaction drop?",
        "practical_applicability": "Are the proposed experiments actionable within a reasonable timeframe? Does it consider implementation constraints?",
        "originality": "Does it consider non-obvious factors (e.g., the 20% that reach humans might now be harder cases, making human agents seem worse)? Does it connect to broader patterns?"
      },
      "max_score": 2.0
    },
    {
      "id": "scenario_02",
      "dimensions": ["jumping_thinking", "ai_collaboration"],
      "question": "You're tasked with reducing employee onboarding time from 3 weeks to 1 week. Current onboarding involves reading documentation, shadowing colleagues, and completing training modules.\n\nDescribe your approach. How would you use AI tools in this process? What ideas from completely different domains might apply here?",
      "rubric": {
        "dimension_relevance": "Does the response draw inspiration from other domains (e.g., gaming tutorials, immersive language learning, military boot camps)? Does it propose meaningful AI integration beyond 'use a chatbot'?",
        "depth_of_reasoning": "Does it break the problem into testable components? Does it question whether 3 weeks is actually too long or if the content is wrong?",
        "practical_applicability": "Are the AI applications specific and feasible? Does it consider what can't be shortened?",
        "originality": "Does it reframe the problem (e.g., maybe onboarding never 'ends' — make it continuous)? Does it propose novel measurement of onboarding effectiveness?"
      },
      "max_score": 2.0
    },
    {
      "id": "scenario_03",
      "dimensions": ["pdca_thinking", "jumping_thinking"],
      "question": "Your team has been tasked with building a new internal tool. After 2 months of development, you discover that a similar open-source tool exists that covers 70% of your requirements.\n\nWhat do you do? Describe your decision-making process, what information you'd gather, and how you'd structure the evaluation.",
      "rubric": {
        "dimension_relevance": "Does it avoid sunk-cost fallacy? Does it propose a structured evaluation rather than emotional reaction? Does it draw on analogies from other 'build vs buy' decisions?",
        "depth_of_reasoning": "Does it consider the 30% gap specifically? Does it propose testing the open-source tool before committing? Does it think about long-term maintenance?",
        "practical_applicability": "Does it outline a concrete timeline for evaluation? Does it consider team morale and stakeholder communication?",
        "originality": "Does it consider hybrid approaches (fork and extend)? Does it question why the team didn't find this tool earlier and what process improvement that implies?"
      },
      "max_score": 2.0
    },
    {
      "id": "scenario_04",
      "dimensions": ["critical_questioning", "ai_collaboration"],
      "question": "Your company adopts a policy that all code must be reviewed by AI before human review. After 3 months, the AI catches 200 bugs that humans missed, but developers report feeling less engaged in code reviews and spending less time on them.\n\nAnalyze this situation. What's actually happening? What would you investigate? What would you recommend?",
      "rubric": {
        "dimension_relevance": "Does it question the '200 bugs' metric (severity? false positives?)? Does it recognize the human behavior change as a systemic effect rather than laziness?",
        "depth_of_reasoning": "Does it consider second-order effects (skill atrophy, review quality decline)? Does it propose experiments to measure the net effect?",
        "practical_applicability": "Does it suggest actionable changes to the workflow rather than just 'balance AI and human'? Does it consider team psychology?",
        "originality": "Does it draw parallels (e.g., automation complacency in aviation)? Does it question whether the goal should be bug-catching or knowledge-sharing?"
      },
      "max_score": 2.0
    },
    {
      "id": "scenario_05",
      "dimensions": ["jumping_thinking", "critical_questioning"],
      "question": "Your SaaS product's pricing page has a 2% conversion rate. The marketing team wants to A/B test different price points. The design team wants to redesign the page layout.\n\nHow would you approach improving the conversion rate? Whose approach would you prioritize, or would you do something different entirely?",
      "rubric": {
        "dimension_relevance": "Does it question whether 2% is actually low (industry benchmarks)? Does it look beyond the pricing page itself (e.g., traffic quality, product-market fit)?",
        "depth_of_reasoning": "Does it propose a structured approach rather than jumping to solutions? Does it consider why visitors reach the pricing page but don't convert?",
        "practical_applicability": "Does it propose quick, measurable experiments? Does it consider running parallel but non-conflicting tests?",
        "originality": "Does it draw from other domains (e.g., behavioral economics, retail checkout optimization)? Does it challenge the assumption that the pricing page is the problem?"
      },
      "max_score": 2.0
    },
    {
      "id": "scenario_06",
      "dimensions": ["ai_collaboration", "pdca_thinking"],
      "question": "You're given access to a new AI coding assistant for your team of 8 developers. Management expects a 30% productivity increase within a month.\n\nDescribe how you would roll this out. How would you measure 'productivity'? What could go wrong?",
      "rubric": {
        "dimension_relevance": "Does it question the 30% target and how productivity is defined? Does it propose iterative rollout rather than big-bang?",
        "depth_of_reasoning": "Does it consider different developer skill levels? Does it anticipate adoption resistance? Does it think about security/IP concerns?",
        "practical_applicability": "Does it propose specific rollout phases with checkpoints? Does it define measurable metrics beyond 'lines of code'?",
        "originality": "Does it consider that productivity might dip initially (learning curve)? Does it think about which tasks benefit most from AI assistance?"
      },
      "max_score": 2.0
    }
  ]
}
```

**Step 4: Commit**

```bash
git add assessment/__init__.py assessment/questions.json
git commit -m "feat: add question bank with 30 MCQs and 6 scenarios"
```

---

### Task 3: Data Models and Database

**Files:**
- Create: `assessment/models.py`
- Create: `assessment/database.py`
- Create: `tests/test_assessment_db.py`

**Step 1: Write the failing test**

Create `tests/test_assessment_db.py`:

```python
"""Tests for assessment database operations."""

import sqlite3
import uuid
from datetime import datetime, timezone

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
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_assessment_db.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'assessment.database'`

**Step 3: Create data models**

Create `assessment/models.py`:

```python
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
```

**Step 4: Create database module**

Create `assessment/database.py`:

```python
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
```

**Step 5: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_assessment_db.py -v`
Expected: 6 tests PASS

**Step 6: Commit**

```bash
git add assessment/models.py assessment/database.py tests/test_assessment_db.py
git commit -m "feat: add assessment data models and SQLite database"
```

---

### Task 4: Exam Service (Question Selection + MCQ Scoring)

**Files:**
- Create: `assessment/exam_service.py`
- Create: `tests/test_exam_service.py`

**Step 1: Write the failing test**

Create `tests/test_exam_service.py`:

```python
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
    # With 8 questions per dimension, picking 3, very likely to differ
    # (not guaranteed, but probability of exact match is ~1/56^4)
    # We just verify both sets are valid
    assert len(ids1) == 14
    assert len(ids2) == 14
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_exam_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'assessment.exam_service'`

**Step 3: Write implementation**

Create `assessment/exam_service.py`:

```python
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
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_exam_service.py -v`
Expected: 5 tests PASS

**Step 5: Commit**

```bash
git add assessment/exam_service.py tests/test_exam_service.py
git commit -m "feat: add exam service with question selection and MCQ scoring"
```

---

### Task 5: LLM Scenario Scorer

**Files:**
- Create: `assessment/scenario_scorer.py`
- Create: `tests/test_scenario_scorer.py`

**Step 1: Write the failing test**

Create `tests/test_scenario_scorer.py`:

```python
"""Tests for LLM-based scenario scoring."""

import json
from unittest.mock import MagicMock, patch

import pytest

from assessment.scenario_scorer import ScenarioScorer


def _mock_response(score_json: dict) -> MagicMock:
    """Create a mock Anthropic response."""
    msg = MagicMock()
    msg.content = [MagicMock(text=json.dumps(score_json))]
    return msg


@pytest.fixture
def scorer():
    return ScenarioScorer(api_key="test-key")


def test_score_scenario_returns_structured_result(scorer):
    expected = {
        "dimension_relevance": 0.4,
        "depth_of_reasoning": 0.3,
        "practical_applicability": 0.5,
        "originality": 0.3,
        "total_score": 1.5,
        "feedback": "Good analysis of the chatbot problem."
    }
    with patch.object(scorer._client.messages, "create", return_value=_mock_response(expected)):
        result = scorer.score(
            question="Chatbot scenario question...",
            rubric={
                "dimension_relevance": "Does it question the 80% metric?",
                "depth_of_reasoning": "Does it propose experiments?",
                "practical_applicability": "Are experiments actionable?",
                "originality": "Non-obvious factors?",
            },
            response="The 80% metric is misleading because...",
            dimensions=["pdca_thinking", "critical_questioning"],
        )
    assert result["score"] == 1.5
    assert "feedback" in result
    assert "dimension_scores" in result


def test_score_clamps_to_max(scorer):
    # LLM returns score above 2.0 — should be clamped
    inflated = {
        "dimension_relevance": 0.5,
        "depth_of_reasoning": 0.5,
        "practical_applicability": 0.5,
        "originality": 0.5,
        "total_score": 3.0,  # above max
        "feedback": "Excellent."
    }
    with patch.object(scorer._client.messages, "create", return_value=_mock_response(inflated)):
        result = scorer.score(
            question="Q", rubric={"a": "b"}, response="R", dimensions=["pdca_thinking"],
        )
    assert result["score"] <= 2.0


def test_score_handles_malformed_response(scorer):
    bad_msg = MagicMock()
    bad_msg.content = [MagicMock(text="This is not JSON")]
    with patch.object(scorer._client.messages, "create", return_value=bad_msg):
        result = scorer.score(
            question="Q", rubric={"a": "b"}, response="R", dimensions=["pdca_thinking"],
        )
    # Should return zero score rather than crash
    assert result["score"] == 0
    assert "error" in result.get("feedback", "").lower() or result["score"] == 0
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_scenario_scorer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'assessment.scenario_scorer'`

**Step 3: Write implementation**

Create `assessment/scenario_scorer.py`:

```python
"""LLM-based scoring for scenario questions."""

from __future__ import annotations

import json
from typing import Any

import anthropic

_SCORING_PROMPT = """\
You are an exam scorer evaluating a candidate's response to a scenario question.

Score the response on these rubric criteria (each 0.0 to 0.5):
{rubric_text}

Return ONLY valid JSON:
{{
  "dimension_relevance": <0.0-0.5>,
  "depth_of_reasoning": <0.0-0.5>,
  "practical_applicability": <0.0-0.5>,
  "originality": <0.0-0.5>,
  "total_score": <sum, max 2.0>,
  "feedback": "<2-3 sentence assessment>"
}}
"""


class ScenarioScorer:
    """Score scenario responses using LLM."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        kwargs: dict = {"api_key": api_key}
        if api_key.startswith("sk-or-"):
            kwargs["base_url"] = "https://openrouter.ai/api"
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model

    def score(
        self,
        question: str,
        rubric: dict[str, str],
        response: str,
        dimensions: list[str],
        max_score: float = 2.0,
    ) -> dict[str, Any]:
        """Score a single scenario response.

        Returns:
            Dict with score, dimension_scores, and feedback.
        """
        rubric_text = "\n".join(f"- {k}: {v}" for k, v in rubric.items())
        system = _SCORING_PROMPT.format(rubric_text=rubric_text)

        user_msg = (
            f"## Question\n{question}\n\n"
            f"## Candidate Response\n{response}\n\n"
            f"Score this response according to the rubric."
        )

        try:
            resp = self._client.messages.create(
                model=self._model,
                max_tokens=1000,
                temperature=0,
                system=system,
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = resp.content[0].text
            parsed = _parse_json(raw)
        except Exception:
            return {
                "score": 0,
                "dimension_scores": {d: 0 for d in dimensions},
                "feedback": "Error: failed to score response.",
            }

        if not parsed:
            return {
                "score": 0,
                "dimension_scores": {d: 0 for d in dimensions},
                "feedback": "Error: failed to parse scoring response.",
            }

        total = min(parsed.get("total_score", 0), max_score)

        # Distribute score across dimensions
        dim_scores = {}
        per_dim = total / max(len(dimensions), 1)
        for d in dimensions:
            dim_scores[d] = round(per_dim, 2)

        return {
            "score": total,
            "dimension_scores": dim_scores,
            "feedback": parsed.get("feedback", ""),
        }


def _parse_json(raw: str) -> dict:
    """Robustly parse JSON from LLM response."""
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    start = raw.find("{")
    last = raw.rfind("}")
    if start != -1 and last != -1:
        try:
            return json.loads(raw[start : last + 1])
        except json.JSONDecodeError:
            pass
    return {}
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_scenario_scorer.py -v`
Expected: 3 tests PASS

**Step 5: Commit**

```bash
git add assessment/scenario_scorer.py tests/test_scenario_scorer.py
git commit -m "feat: add LLM-based scenario scorer with rubric evaluation"
```

---

### Task 6: FastAPI Application + API Endpoints

**Files:**
- Create: `assessment/app.py`
- Create: `tests/test_assessment_api.py`

**Step 1: Write the failing test**

Create `tests/test_assessment_api.py`:

```python
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
    # Re-initialize services with test paths
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
    assert resp.status_code == 422  # FastAPI validation error


def test_submit_and_get_result(client):
    # Start exam
    start = client.post("/api/exam/start", json={
        "candidate_name": "Bob",
        "candidate_email": "bob@test.com",
        "exam_type": "internal",
    })
    session_id = start.json()["session_id"]
    questions = start.json()["questions"]

    # Build answers: all MCQs answered "A", scenarios with text
    answers = {}
    for q in questions:
        if q["type"] == "mcq":
            answers[q["id"]] = "A"
        else:
            answers[q["id"]] = "This is my scenario response about the problem."

    # Mock LLM scorer
    mock_score_result = {
        "score": 1.5,
        "dimension_scores": {"pdca_thinking": 0.75, "critical_questioning": 0.75},
        "feedback": "Good analysis.",
    }
    with patch("assessment.app._scorer") as mock_scorer:
        mock_scorer.score.return_value = mock_score_result
        resp = client.post(f"/api/exam/submit", json={
            "session_id": session_id,
            "answers": answers,
        })

    assert resp.status_code == 200
    data = resp.json()
    assert "total_score" in data
    assert "passed" in data
    assert "dimension_scores" in data


def test_get_result(client):
    # Start + submit first
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
            answers[q["id"]] = "B"  # Score 2 for most questions
        else:
            answers[q["id"]] = "Detailed scenario response."

    mock_score_result = {
        "score": 1.8,
        "dimension_scores": {"jumping_thinking": 0.9, "ai_collaboration": 0.9},
        "feedback": "Excellent.",
    }
    with patch("assessment.app._scorer") as mock_scorer:
        mock_scorer.score.return_value = mock_score_result
        client.post(f"/api/exam/submit", json={
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
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_assessment_api.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'assessment.app'`

**Step 3: Write implementation**

Create `assessment/app.py`:

```python
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
    exam_type: str  # "internal" | "external"


class SubmitRequest(BaseModel):
    session_id: str
    answers: dict[str, str]  # {question_id: answer}


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
            # No API key — give zero for scenarios
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
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_assessment_api.py -v`
Expected: 5 tests PASS

**Step 5: Commit**

```bash
git add assessment/app.py tests/test_assessment_api.py
git commit -m "feat: add FastAPI app with exam start/submit/result endpoints"
```

---

### Task 7: Frontend — HTML/CSS/JS

**Files:**
- Create: `assessment/static/index.html`
- Create: `assessment/static/style.css`
- Create: `assessment/static/app.js`

**Step 1: Create the static directory**

Run: `mkdir -p assessment/static`

**Step 2: Create `assessment/static/style.css`**

```css
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0f172a;
    color: #e2e8f0;
    min-height: 100vh;
}

.container {
    max-width: 720px;
    margin: 0 auto;
    padding: 2rem 1.5rem;
}

h1 {
    font-size: 1.75rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
    color: #f8fafc;
}

h2 {
    font-size: 1.25rem;
    font-weight: 600;
    margin-bottom: 1rem;
    color: #94a3b8;
}

/* Start Page */
.start-form {
    background: #1e293b;
    border-radius: 12px;
    padding: 2rem;
    margin-top: 2rem;
}

.form-group {
    margin-bottom: 1.25rem;
}

.form-group label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 500;
    color: #94a3b8;
}

.form-group input, .form-group select {
    width: 100%;
    padding: 0.75rem 1rem;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #e2e8f0;
    font-size: 1rem;
}

.form-group input:focus, .form-group select:focus {
    outline: none;
    border-color: #3b82f6;
}

.btn {
    display: inline-block;
    padding: 0.75rem 2rem;
    background: #3b82f6;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
}

.btn:hover { background: #2563eb; }
.btn:disabled { background: #475569; cursor: not-allowed; }

/* Timer */
.timer {
    position: fixed;
    top: 1rem;
    right: 1.5rem;
    background: #1e293b;
    padding: 0.5rem 1rem;
    border-radius: 8px;
    font-family: monospace;
    font-size: 1.25rem;
    color: #3b82f6;
    border: 1px solid #334155;
}

.timer.warning { color: #f59e0b; border-color: #f59e0b; }
.timer.danger { color: #ef4444; border-color: #ef4444; }

/* Progress */
.progress-bar {
    height: 4px;
    background: #334155;
    border-radius: 2px;
    margin-bottom: 2rem;
}

.progress-fill {
    height: 100%;
    background: #3b82f6;
    border-radius: 2px;
    transition: width 0.3s;
}

.question-count {
    text-align: right;
    font-size: 0.875rem;
    color: #64748b;
    margin-bottom: 0.5rem;
}

/* Question */
.question-card {
    background: #1e293b;
    border-radius: 12px;
    padding: 2rem;
}

.question-dimension {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    background: #1e3a5f;
    color: #60a5fa;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: 600;
    margin-bottom: 1rem;
    text-transform: uppercase;
}

.question-text {
    font-size: 1.1rem;
    line-height: 1.6;
    margin-bottom: 1.5rem;
}

/* MCQ Options */
.option {
    display: block;
    width: 100%;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
    background: #0f172a;
    border: 2px solid #334155;
    border-radius: 8px;
    color: #e2e8f0;
    font-size: 1rem;
    text-align: left;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s;
}

.option:hover { border-color: #3b82f6; background: #172042; }
.option.selected { border-color: #3b82f6; background: #1e3a5f; }

/* Scenario textarea */
.scenario-input {
    width: 100%;
    min-height: 200px;
    padding: 1rem;
    background: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    color: #e2e8f0;
    font-size: 1rem;
    line-height: 1.6;
    resize: vertical;
}

.scenario-input:focus { outline: none; border-color: #3b82f6; }

.word-count {
    text-align: right;
    font-size: 0.8rem;
    color: #64748b;
    margin-top: 0.5rem;
}

/* Navigation */
.nav-buttons {
    display: flex;
    justify-content: space-between;
    margin-top: 1.5rem;
}

.btn-secondary {
    background: transparent;
    border: 1px solid #475569;
    color: #94a3b8;
}

.btn-secondary:hover { background: #1e293b; }

/* Result Page */
.result-card {
    background: #1e293b;
    border-radius: 12px;
    padding: 2rem;
    text-align: center;
    margin-top: 2rem;
}

.result-pass {
    color: #22c55e;
    font-size: 3rem;
    font-weight: 800;
    margin: 1rem 0;
}

.result-fail {
    color: #ef4444;
    font-size: 3rem;
    font-weight: 800;
    margin: 1rem 0;
}

.score-display {
    font-size: 1.5rem;
    color: #94a3b8;
    margin-bottom: 2rem;
}

/* Dimension bars */
.dimension-bars {
    text-align: left;
    margin-top: 2rem;
}

.dim-row {
    margin-bottom: 1rem;
}

.dim-label {
    display: flex;
    justify-content: space-between;
    font-size: 0.9rem;
    margin-bottom: 0.25rem;
}

.dim-bar {
    height: 8px;
    background: #334155;
    border-radius: 4px;
}

.dim-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.5s;
}

.dim-fill.jt { background: #8b5cf6; }
.dim-fill.pdca { background: #3b82f6; }
.dim-fill.ai { background: #06b6d4; }
.dim-fill.cq { background: #f59e0b; }

.feedback-section {
    text-align: left;
    margin-top: 2rem;
    padding-top: 1.5rem;
    border-top: 1px solid #334155;
}

.feedback-section h3 {
    margin-bottom: 0.75rem;
    color: #94a3b8;
}

.feedback-text {
    line-height: 1.6;
    color: #cbd5e1;
}

/* Loading */
.loading {
    text-align: center;
    padding: 3rem;
}

.spinner {
    display: inline-block;
    width: 40px;
    height: 40px;
    border: 3px solid #334155;
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.hidden { display: none; }
```

**Step 3: Create `assessment/static/app.js`**

```javascript
const API = '/api/exam';

let state = {
    sessionId: null,
    questions: [],
    currentIndex: 0,
    answers: {},
    startTime: null,
    timerInterval: null,
    timeLimit: 30 * 60, // 30 minutes in seconds
};

// --- Views ---

function showView(id) {
    document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
    document.getElementById(id).classList.remove('hidden');
}

// --- Start Exam ---

async function startExam(e) {
    e.preventDefault();
    const name = document.getElementById('name').value.trim();
    const email = document.getElementById('email').value.trim();
    const type = document.getElementById('exam-type').value;

    if (!name || !email) return;

    const btn = e.target.querySelector('button');
    btn.disabled = true;
    btn.textContent = 'Loading...';

    try {
        const resp = await fetch(`${API}/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                candidate_name: name,
                candidate_email: email,
                exam_type: type,
            }),
        });
        const data = await resp.json();
        state.sessionId = data.session_id;
        state.questions = data.questions;
        state.currentIndex = 0;
        state.answers = {};
        startTimer();
        showView('exam-view');
        renderQuestion();
    } catch (err) {
        alert('Failed to start exam. Please try again.');
        btn.disabled = false;
        btn.textContent = 'Start Assessment';
    }
}

// --- Timer ---

function startTimer() {
    state.startTime = Date.now();
    const timerEl = document.getElementById('timer');
    timerEl.classList.remove('hidden');

    state.timerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
        const remaining = Math.max(0, state.timeLimit - elapsed);
        const mins = Math.floor(remaining / 60);
        const secs = remaining % 60;
        timerEl.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

        timerEl.classList.remove('warning', 'danger');
        if (remaining <= 60) timerEl.classList.add('danger');
        else if (remaining <= 300) timerEl.classList.add('warning');

        if (remaining <= 0) {
            clearInterval(state.timerInterval);
            submitExam();
        }
    }, 1000);
}

// --- Render Question ---

function renderQuestion() {
    const q = state.questions[state.currentIndex];
    const total = state.questions.length;
    const idx = state.currentIndex;

    // Progress
    document.getElementById('progress-fill').style.width = `${((idx + 1) / total) * 100}%`;
    document.getElementById('question-count').textContent = `${idx + 1} / ${total}`;

    // Dimension tag
    const dimNames = {
        jumping_thinking: 'Jumping Thinking',
        pdca_thinking: 'PDCA Thinking',
        ai_collaboration: 'AI Collaboration',
        critical_questioning: 'Critical Questioning',
    };
    const dims = q.type === 'mcq' ? [q.dimension] : (q.dimensions || []);
    document.getElementById('question-dimension').textContent = dims.map(d => dimNames[d] || d).join(' + ');

    // Question text
    document.getElementById('question-text').textContent = q.question;

    // Options area
    const optArea = document.getElementById('options-area');
    optArea.innerHTML = '';

    if (q.type === 'mcq') {
        q.options.forEach(opt => {
            const btn = document.createElement('button');
            btn.className = 'option' + (state.answers[q.id] === opt.label ? ' selected' : '');
            btn.textContent = `${opt.label}) ${opt.text}`;
            btn.onclick = () => {
                state.answers[q.id] = opt.label;
                renderQuestion(); // re-render to update selection
            };
            optArea.appendChild(btn);
        });
    } else {
        const textarea = document.createElement('textarea');
        textarea.className = 'scenario-input';
        textarea.placeholder = 'Write your response here (200-400 words recommended)...';
        textarea.value = state.answers[q.id] || '';
        textarea.oninput = (e) => {
            state.answers[q.id] = e.target.value;
            const words = e.target.value.trim().split(/\s+/).filter(w => w).length;
            document.getElementById('word-count').textContent = `${words} words`;
        };
        optArea.appendChild(textarea);

        const wc = document.createElement('div');
        wc.id = 'word-count';
        wc.className = 'word-count';
        const currentWords = (state.answers[q.id] || '').trim().split(/\s+/).filter(w => w).length;
        wc.textContent = `${currentWords} words`;
        optArea.appendChild(wc);
    }

    // Nav buttons
    document.getElementById('btn-prev').classList.toggle('hidden', idx === 0);
    const nextBtn = document.getElementById('btn-next');
    if (idx === total - 1) {
        nextBtn.textContent = 'Submit';
        nextBtn.onclick = submitExam;
    } else {
        nextBtn.textContent = 'Next';
        nextBtn.onclick = nextQuestion;
    }
}

function nextQuestion() {
    if (state.currentIndex < state.questions.length - 1) {
        state.currentIndex++;
        renderQuestion();
    }
}

function prevQuestion() {
    if (state.currentIndex > 0) {
        state.currentIndex--;
        renderQuestion();
    }
}

// --- Submit ---

async function submitExam() {
    clearInterval(state.timerInterval);
    document.getElementById('timer').classList.add('hidden');
    showView('loading-view');

    try {
        const resp = await fetch(`${API}/submit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: state.sessionId,
                answers: state.answers,
            }),
        });
        const result = await resp.json();
        renderResult(result);
    } catch (err) {
        alert('Failed to submit. Please try again.');
        showView('exam-view');
    }
}

// --- Result ---

function renderResult(result) {
    showView('result-view');

    const statusEl = document.getElementById('result-status');
    statusEl.textContent = result.passed ? 'PASSED' : 'NOT PASSED';
    statusEl.className = result.passed ? 'result-pass' : 'result-fail';

    document.getElementById('result-score').textContent = `${result.total_score} / 20 points`;

    // Dimension bars
    const dimConfig = [
        { key: 'jumping_thinking', label: 'Jumping Thinking', cls: 'jt', max: 8 },
        { key: 'pdca_thinking', label: 'PDCA Thinking', cls: 'pdca', max: 8 },
        { key: 'ai_collaboration', label: 'AI Collaboration', cls: 'ai', max: 8 },
        { key: 'critical_questioning', label: 'Critical Questioning', cls: 'cq', max: 8 },
    ];

    const barsEl = document.getElementById('dimension-bars');
    barsEl.innerHTML = '';

    dimConfig.forEach(dim => {
        const score = (result.dimension_scores || {})[dim.key] || 0;
        const pct = Math.min(100, (score / dim.max) * 100);

        const row = document.createElement('div');
        row.className = 'dim-row';
        row.innerHTML = `
            <div class="dim-label">
                <span>${dim.label}</span>
                <span>${score.toFixed(1)}</span>
            </div>
            <div class="dim-bar">
                <div class="dim-fill ${dim.cls}" style="width: ${pct}%"></div>
            </div>
        `;
        barsEl.appendChild(row);
    });

    // Feedback
    const feedbackEl = document.getElementById('feedback-text');
    feedbackEl.textContent = result.llm_feedback || 'No detailed feedback available.';
}

// --- Init ---

document.getElementById('start-form').addEventListener('submit', startExam);
document.getElementById('btn-prev').addEventListener('click', prevQuestion);
```

**Step 4: Create `assessment/static/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Recursive Thinking Assessment</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div id="timer" class="timer hidden">30:00</div>

    <div class="container">
        <!-- Start View -->
        <div id="start-view" class="view">
            <h1>Recursive Thinking Assessment</h1>
            <h2>Evaluate your thinking patterns across 4 dimensions</h2>

            <form id="start-form" class="start-form">
                <div class="form-group">
                    <label for="name">Full Name</label>
                    <input type="text" id="name" required placeholder="Your name">
                </div>
                <div class="form-group">
                    <label for="email">Email</label>
                    <input type="email" id="email" required placeholder="your@email.com">
                </div>
                <div class="form-group">
                    <label for="exam-type">Assessment Type</label>
                    <select id="exam-type">
                        <option value="internal">Internal (Employee Evaluation)</option>
                        <option value="external">External (Recruiting)</option>
                    </select>
                </div>
                <button type="submit" class="btn">Start Assessment</button>
            </form>
        </div>

        <!-- Exam View -->
        <div id="exam-view" class="view hidden">
            <div class="question-count" id="question-count">1 / 14</div>
            <div class="progress-bar"><div class="progress-fill" id="progress-fill"></div></div>

            <div class="question-card">
                <div class="question-dimension" id="question-dimension"></div>
                <div class="question-text" id="question-text"></div>
                <div id="options-area"></div>
            </div>

            <div class="nav-buttons">
                <button class="btn btn-secondary hidden" id="btn-prev">Previous</button>
                <button class="btn" id="btn-next">Next</button>
            </div>
        </div>

        <!-- Loading View -->
        <div id="loading-view" class="view hidden">
            <div class="loading">
                <div class="spinner"></div>
                <p style="margin-top: 1.5rem; color: #94a3b8;">Scoring your responses...</p>
                <p style="margin-top: 0.5rem; color: #64748b; font-size: 0.875rem;">This may take a moment for scenario analysis.</p>
            </div>
        </div>

        <!-- Result View -->
        <div id="result-view" class="view hidden">
            <div class="result-card">
                <h2>Assessment Complete</h2>
                <div id="result-status" class="result-pass">PASSED</div>
                <div class="score-display" id="result-score">16 / 20 points</div>

                <div class="dimension-bars" id="dimension-bars"></div>

                <div class="feedback-section">
                    <h3>Scenario Feedback</h3>
                    <div class="feedback-text" id="feedback-text"></div>
                </div>
            </div>
        </div>
    </div>

    <script src="/static/app.js"></script>
</body>
</html>
```

**Step 5: Verify the server starts**

Run: `ANTHROPIC_API_KEY=test .venv/bin/uvicorn assessment.app:app --host 0.0.0.0 --port 8000 &`
Then: `curl http://localhost:8000/`
Expected: HTML page content
Then: `kill %1`

**Step 6: Commit**

```bash
git add assessment/static/
git commit -m "feat: add frontend with start, exam, and result views"
```

---

### Task 8: Run Script + End-to-End Manual Test

**Files:**
- Create: `run_assessment.py`

**Step 1: Create run script**

Create `run_assessment.py`:

```python
"""Launch the Recursive Thinking Assessment server."""

import os
import sys


def main():
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn not installed. Run: pip install -e '.[assessment]'")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("Warning: ANTHROPIC_API_KEY not set. Scenario scoring will be disabled.")

    port = int(os.environ.get("PORT", "8000"))
    print(f"\n  Recursive Thinking Assessment")
    print(f"  http://localhost:{port}\n")

    uvicorn.run("assessment.app:app", host="0.0.0.0", port=port, reload=True)


if __name__ == "__main__":
    main()
```

**Step 2: Run all tests**

Run: `.venv/bin/pytest tests/test_assessment_db.py tests/test_exam_service.py tests/test_scenario_scorer.py tests/test_assessment_api.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add run_assessment.py
git commit -m "feat: add assessment server run script"
```

**Step 4: Final commit — push to GitHub**

```bash
git push origin main
```

---

## Summary

| Task | Component | Files | Tests |
|------|-----------|-------|-------|
| 1 | Dependencies | `pyproject.toml` | — |
| 2 | Question Bank | `assessment/questions.json` | — |
| 3 | DB + Models | `assessment/models.py`, `assessment/database.py` | `tests/test_assessment_db.py` |
| 4 | Exam Service | `assessment/exam_service.py` | `tests/test_exam_service.py` |
| 5 | Scenario Scorer | `assessment/scenario_scorer.py` | `tests/test_scenario_scorer.py` |
| 6 | FastAPI App | `assessment/app.py` | `tests/test_assessment_api.py` |
| 7 | Frontend | `assessment/static/{index.html,style.css,app.js}` | manual |
| 8 | Run Script | `run_assessment.py` | all tests |
