"""Stage 1: InterfacePlanGenerator — PRD → interface_plan.json.

Extracts screen inventory and navigation relationships from a PRD document.
Follows WIREFRAME_GENERATION_GUIDE.md Section 4.
"""

from __future__ import annotations

import json
from typing import Any

import anthropic


_INTERFACE_PLAN_SYSTEM_PROMPT = """\
You are a UI/UX architect. Given a PRD (Product Requirements Document), \
extract all screens (pages and popups) the product needs, and determine \
their navigation relationships.

Rules:
1. Each screen has type "page" (full-screen) or "popup" (overlay/modal).
2. Popups have a "belongs_to" field pointing to their parent page.
3. Navigation edges: navigation_from = screens that can reach this one, \
navigation_to = screens reachable from this one.
4. Include ALL screens implied by the PRD — menus, gameplay, settings, \
modals, overlays, HUD, etc.
5. Use global_resolution 1080x1920 (portrait mobile) unless PRD specifies otherwise.
6. Screen descriptions should describe CONTENT and LOGIC, not layout positions.
7. Use the same language as the PRD for screen names and descriptions.
8. Match screen count to product complexity:
   - Simple/arcade games (Flappy Bird, Tetris): 3-5 screens. \
Include score/leaderboard popup if the game has scoring. \
NO settings, NO tutorials, NO pause menus unless PRD explicitly requires them.
   - Casual games (PvZ, Angry Birds): 5-7 screens.
   - Mid-core/complex games: 6-10 screens.
   - Apps/SaaS: match to feature count in PRD.
   IMPORTANT: Do NOT add screens the PRD doesn't describe or imply. \
Every screen must be justified by specific PRD content.
9. For games with scoring, ALWAYS include a leaderboard popup screen \
with id="leaderboard" (type "popup", belongs_to the game_over or result screen). \
The leaderboard MUST be accessible from both the main menu AND the game_over screen. \
Do NOT rename it to "best_scores", "high_scores", or "ranking" — use id="leaderboard".
10. navigation_from and navigation_to MUST be symmetric: \
if screen A lists B in navigation_to, screen B MUST list A in navigation_from.
11. Popups should be reachable from ALL screens that show a button for them. \
For example, if both the start menu and game_over screen have a leaderboard button, \
the leaderboard popup's navigation_from must include BOTH screens.
12. If the PRD describes a preparation/selection step before gameplay \
(e.g., choosing characters, loadout, plants, cards), create a separate \
popup or page for that selection screen. It should appear between \
the level/menu screen and the gameplay screen.

Return ONLY valid JSON matching this schema:
{
  "game_title": "<product name>",
  "art_style": "<visual style from PRD>",
  "global_resolution": {"width": 1080, "height": 1920},
  "total_interfaces": <number>,
  "entry_interface": "<id of first screen>",
  "interfaces": [
    {
      "index": <1-based>,
      "id": "<snake_case_id>",
      "name": "<display name>",
      "type": "page|popup",
      "dimensions": {"width": 1080, "height": 1920},
      "description": "<what this screen shows and does>",
      "belongs_to": null or "<parent_page_id>",
      "navigation_from": ["<screen_ids>"],
      "navigation_to": ["<screen_ids>"]
    }
  ]
}
"""


class InterfacePlanGenerator:
    """Generate interface plan from PRD document."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        kwargs: dict = {"api_key": api_key}
        if api_key.startswith("sk-or-"):
            kwargs["base_url"] = "https://openrouter.ai/api"
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model

    def generate(self, prd_document: str) -> dict[str, Any]:
        """Generate interface plan from PRD text.

        Args:
            prd_document: Full PRD markdown text.

        Returns:
            interface_plan dict matching WIREFRAME_GENERATION_GUIDE.md format.
        """
        response = self._client.messages.create(
            model=self._model,
            max_tokens=8000,
            temperature=0.3,
            system=_INTERFACE_PLAN_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": (
                f"## PRD Document\n\n{prd_document}\n\n"
                "Generate the interface plan JSON."
            )}],
        )

        raw = response.content[0].text
        return _parse_json(raw)


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
            return json.loads(raw[start:last + 1])
        except json.JSONDecodeError:
            pass
    return {}
