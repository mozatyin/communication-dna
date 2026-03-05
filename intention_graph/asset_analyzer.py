"""Stage 2.1: AssetAnalyzer — PRD + InterfacePlan → asset_table.json.

Derives asset requirements (images, audio, UI elements) from PRD and interface plan.
Analysis only — no actual file generation.
Follows WIREFRAME_GENERATION_GUIDE.md Section 5.
"""

from __future__ import annotations

import json
from typing import Any

import anthropic


_ASSET_ANALYSIS_SYSTEM_PROMPT = """\
You are a game/product asset analyst. Given a PRD and interface plan, \
derive ALL assets needed to build the product.

Asset categories:
- background: Full-screen backgrounds for each screen
- character: Player/NPC sprites (games) or avatars (apps)
- ui: Buttons, icons, panels — use implementation "css" for simple styled elements
- music: Background music tracks
- sfx: Sound effects

Rules:
1. Every screen needs at least a background asset.
2. Buttons and simple UI → implementation: "css" (no image file needed).
3. Complex graphics → implementation: "image" (AI-generated).
4. Each asset has a unique id (snake_case, prefixed by category: bg_, char_, btn_, icon_, bgm_, sfx_).
5. Include dimensions for image assets.
6. Use the same language as the PRD for descriptions.

Return ONLY valid JSON:
{
  "schemaVersion": "asset-table-1.1",
  "meta": {
    "gameTitle": "<name>",
    "gameDescription": "<brief>",
    "artDirection": "<art style>"
  },
  "assets": [
    {
      "id": "<unique_id>",
      "type": "image|audio",
      "category": "background|character|ui|music|sfx",
      "usage": "<which screen/feature uses this>",
      "description": "<visual/audio description>",
      "implementation": "image|css|text",
      "dimensions": {"width": N, "height": N} or null,
      "default_label": "<button text if applicable>",
      "format": "png|mp3",
      "path": "assets/images/<id>.png or assets/audio/<id>.mp3"
    }
  ]
}
"""


class AssetAnalyzer:
    """Analyze asset requirements from PRD + interface plan."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        kwargs: dict = {"api_key": api_key}
        if api_key.startswith("sk-or-"):
            kwargs["base_url"] = "https://openrouter.ai/api"
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model

    def analyze(
        self,
        prd_document: str,
        interface_plan: dict[str, Any],
    ) -> dict[str, Any]:
        """Analyze asset requirements.

        Args:
            prd_document: Full PRD markdown text.
            interface_plan: Output from InterfacePlanGenerator.

        Returns:
            asset_table dict matching WIREFRAME_GENERATION_GUIDE.md format.
        """
        plan_text = json.dumps(interface_plan, ensure_ascii=False, indent=2)

        response = self._client.messages.create(
            model=self._model,
            max_tokens=12000,
            temperature=0.3,
            system=_ASSET_ANALYSIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": (
                f"## PRD Document\n\n{prd_document}\n\n"
                f"## Interface Plan\n\n{plan_text}\n\n"
                "Generate the asset table JSON."
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
