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
