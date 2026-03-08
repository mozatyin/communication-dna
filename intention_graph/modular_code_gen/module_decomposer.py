"""Module Decomposer: break PRD core_systems into code modules."""

from __future__ import annotations

import json
import time
from typing import Any

import anthropic

from intention_graph.modular_code_gen.models import ModuleSpec


_SYSTEM_PROMPT = """\
You are a game architecture decomposer. Given a PRD document, wireframe, \
and list of core_systems, decompose the game into independent code modules.

RULES:
1. MUST include a "game_state" module that owns shared GameState
2. Each module maps to 1-3 core_systems (no 1:1 inflation)
3. Module count based on complexity:
   - arcade: 3-4 modules
   - casual: 4-5 modules
   - mid-core: 5-7 modules
4. Dependencies must be acyclic (no circular deps)
5. Every core_system must be covered by exactly one module
6. Module IDs use snake_case

Return ONLY valid JSON — an array of module objects:
[
  {
    "module_id": "game_state",
    "description": "Manages shared game state, score, lives, game status",
    "core_systems": ["score_system"],
    "dependencies": []
  },
  ...
]
"""


def _parse_json_array(raw: str) -> list[dict]:
    """Robustly parse JSON array from LLM response."""
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass
    start = raw.find("[")
    last = raw.rfind("]")
    if start != -1 and last != -1:
        try:
            result = json.loads(raw[start : last + 1])
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass
    return []


class ModuleDecomposer:
    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
    ):
        kwargs: dict[str, Any] = {"api_key": api_key}
        if api_key.startswith("sk-or-"):
            kwargs["base_url"] = "https://openrouter.ai/api"
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model

    def decompose(
        self,
        prd_document: str,
        wireframe: dict,
        core_systems: list[str],
        complexity: str = "arcade",
    ) -> list[ModuleSpec]:
        """Decompose core_systems into code modules via LLM."""
        user_msg = (
            f"## PRD\n{prd_document[:4000]}\n\n"
            f"## Wireframe summary\n"
            f"Screens: {[i.get('interface_id','?') for i in wireframe.get('interfaces',[])]}\n\n"
            f"## Core Systems\n{json.dumps(core_systems, ensure_ascii=False)}\n\n"
            f"## Complexity: {complexity}\n\n"
            "Return the module decomposition JSON array."
        )

        raw = self._call_with_retry(user_msg)
        items = _parse_json_array(raw)
        if not items:
            raise ValueError("Failed to parse module decomposition from LLM response")

        modules = [ModuleSpec(**item) for item in items]

        # Robust parsing: skip items that fail ModuleSpec construction
        modules = []
        for item in items:
            try:
                modules.append(ModuleSpec(**item))
            except (TypeError, ValueError):
                continue

        if not modules:
            raise ValueError("No valid modules parsed from LLM response")

        # Ensure game_state module exists
        if not any(m.module_id == "game_state" for m in modules):
            modules.insert(
                0,
                ModuleSpec(
                    module_id="game_state",
                    description="Manages shared game state",
                    core_systems=[],
                    dependencies=[],
                ),
            )

        return modules

    def _call_with_retry(self, user_msg: str) -> str:
        """LLM call with retry on rate limit errors."""
        for attempt in range(3):
            try:
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=4096,
                    temperature=0.0,
                    system=_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_msg}],
                )
                return response.content[0].text
            except anthropic.RateLimitError:
                time.sleep((attempt + 1) * 10)
            except anthropic.APIStatusError as e:
                if e.status_code in (403, 429, 529):
                    time.sleep((attempt + 1) * 10)
                else:
                    raise
        raise RuntimeError("Decomposer LLM call failed after 3 retries")
