"""Stage 3: WireframeGenerator — PRD + InterfacePlan + AssetTable → wireframe.json.

Generates pixel-precise UI layouts for each screen.
Follows WIREFRAME_GENERATION_GUIDE.md Section 6.
"""

from __future__ import annotations

import json
from typing import Any

import anthropic


_WIREFRAME_SYSTEM_PROMPT = """\
You are a UI layout designer. Given a PRD, interface plan, and asset table, \
generate precise wireframe layouts for EVERY screen.

Element types:
- "image": references an asset_id from the asset_library
- "text": displays inner_text with style
- "button": clickable, has event="click" and target_interface_id for navigation
- "css": decorative element styled with CSS (background panels, dividers)

Layout rules:
1. Resolution is specified in the interface plan (typically 1080x1920).
2. All positions are ABSOLUTE PIXELS (x, y, width, height).
3. z_index: 0 = background, higher = on top.
4. Background images always at z_index 0, covering full screen.
5. Buttons need event="click" + target_interface_id matching an interface id.
6. Every element in asset_table should appear in at least one interface.
7. Group interfaces into logical modules (menu_flow, gameplay_flow, etc.).
8. Navigation between modules uses module_connections.

Style properties (CSS-like):
- background-color, color, font-size, font-weight, text-align
- border-radius, border, opacity, text-shadow, line-height

Return ONLY valid JSON:
{
  "project": {
    "title": "<name>",
    "global_resolution": {"width": 1080, "height": 1920}
  },
  "asset_library": {
    "<asset_id>": {"type": "image|audio", "path": "<path>", "label": "<desc>"}
  },
  "modules": [
    {"module_id": "<id>", "module_name": "<name>", "description": "<desc>", \
"color": "<hex>", "interface_ids": ["<ids>"]}
  ],
  "module_connections": [
    {"from": "<module_id>", "to": "<module_id>", "label": "<action>"}
  ],
  "interfaces": [
    {
      "interface_id": "<id>",
      "interface_name": "<name>",
      "module_id": "<module_id>",
      "type": "page|popup",
      "parents": ["<ids>"],
      "children": ["<ids>"],
      "dimensions": {"width": 1080, "height": 1920},
      "elements": [
        {
          "id": "<elem_id>",
          "type": "image|text|button|css",
          "asset_id": "<asset_id or null>",
          "inner_text": "<text or null>",
          "rect": {"x": N, "y": N, "width": N, "height": N, "z_index": N},
          "style": {...},
          "event": "click|null",
          "target_interface_id": "<id or null>",
          "element_class": "editable"
        }
      ],
      "bg_music_asset_id": "<asset_id or null>"
    }
  ]
}
"""


class WireframeGenerator:
    """Generate wireframe layouts from PRD + plan + assets."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        kwargs: dict = {"api_key": api_key}
        if api_key.startswith("sk-or-"):
            kwargs["base_url"] = "https://openrouter.ai/api"
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model

    def generate(
        self,
        prd_document: str,
        interface_plan: dict[str, Any],
        asset_table: dict[str, Any],
        reference_wireframe: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate wireframe spec.

        Args:
            prd_document: Full PRD markdown text.
            interface_plan: Output from InterfacePlanGenerator.
            asset_table: Output from AssetAnalyzer.
            reference_wireframe: Optional golden sample for PDCA guidance.

        Returns:
            wireframe dict matching WIREFRAME_GENERATION_GUIDE.md format.
        """
        plan_text = json.dumps(interface_plan, ensure_ascii=False, indent=2)
        asset_text = json.dumps(asset_table, ensure_ascii=False, indent=2)

        user_parts = [
            f"## PRD Document\n\n{prd_document}",
            f"\n## Interface Plan\n\n{plan_text}",
            f"\n## Asset Table\n\n{asset_text}",
        ]

        if reference_wireframe:
            ref_text = json.dumps(reference_wireframe, ensure_ascii=False, indent=2)
            user_parts.append(
                f"\n## Reference Wireframe (Golden Sample)\n\n"
                f"Study this reference wireframe for layout patterns and quality:\n"
                f"{ref_text[:8000]}\n\n"
                f"Generate a wireframe of EQUAL or BETTER quality. "
                f"Match the reference's level of detail for element positioning."
            )

        user_parts.append("\nGenerate the wireframe JSON.")

        response = self._client.messages.create(
            model=self._model,
            max_tokens=20000,
            temperature=0.4,
            system=_WIREFRAME_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": "\n".join(user_parts)}],
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
