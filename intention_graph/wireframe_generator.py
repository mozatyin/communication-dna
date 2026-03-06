"""Stage 3: WireframeGenerator — PRD + InterfacePlan + AssetTable → wireframe.json.

Generates pixel-precise UI layouts for each screen.
Follows WIREFRAME_GENERATION_GUIDE.md Section 6.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import anthropic

from intention_graph.wireframe_quality import evaluate


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
9. parents and children MUST match the interface plan exactly. \
If the plan says screen A navigates to B, then A's children must include B \
and B's parents must include A.
10. Every button with event="click" MUST have a target_interface_id \
pointing to a valid interface_id (except gameplay action buttons).
11. Generate EXACTLY the screens listed in the interface plan — no more, no fewer.
12. Popup screens should be SIMPLE — typically 3-6 elements: \
a background panel (css), title text, content, and close/action button. \
Do NOT over-engineer popups with decorative elements.
13. MUST use "image" type elements with asset_id for ALL image assets \
in the asset_table. Every page should have at least one "image" element \
(typically the background). Do NOT replace image assets with "css" elements.
14. Target element counts per screen type: \
Menu/title screens: 4-7 elements. \
Gameplay screens: 7-12 elements. \
Popups: 3-5 elements. \
Do NOT add decorative CSS elements beyond what is needed for visual structure.
15. Every navigation button MUST have a target_interface_id. \
Use the interface_id from the plan that matches the button's purpose. \
For example: "返回主菜单" → main_menu, "重新开始" → gameplay, \
"排行榜" → leaderboard, "开始游戏" → gameplay or level_select.

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
        kwargs: dict = {"api_key": api_key, "timeout": 600.0}
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

        chunks: list[str] = []
        with self._client.messages.stream(
            model=self._model,
            max_tokens=32000,
            temperature=0.2,
            system=_WIREFRAME_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": "\n".join(user_parts)}],
        ) as stream:
            for text in stream.text_stream:
                chunks.append(text)

        raw = "".join(chunks)
        wireframe = _parse_json(raw)
        wireframe = _validate_against_plan(wireframe, interface_plan)
        return _infer_button_targets(wireframe)


    def generate_best_of_n(
        self,
        prd_document: str,
        interface_plan: dict[str, Any],
        asset_table: dict[str, Any],
        golden_wireframe: dict[str, Any],
        n: int = 3,
        reference_wireframe: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], float]:
        """Generate N wireframes and return the best one by structural score.

        Args:
            prd_document: Full PRD markdown text.
            interface_plan: Output from InterfacePlanGenerator.
            asset_table: Output from AssetAnalyzer.
            golden_wireframe: Golden sample for evaluation scoring.
            n: Number of candidates to generate.
            reference_wireframe: Optional golden sample for PDCA guidance.

        Returns:
            Tuple of (best_wireframe, best_score).
        """
        best_wf = None
        best_score = -1.0

        for i in range(n):
            try:
                wf = self.generate(
                    prd_document, interface_plan, asset_table, reference_wireframe
                )
                report = evaluate(wf, golden_wireframe)
                score = report.overall_score
                print(f"  [Best-of-{n}] Candidate {i+1}/{n}: {score:.0%}", file=sys.stderr)
                if score > best_score:
                    best_score = score
                    best_wf = wf
            except Exception as e:
                print(f"  [Best-of-{n}] Candidate {i+1}/{n} failed: {e}", file=sys.stderr)
                continue

        if best_wf is None:
            raise RuntimeError(f"All {n} candidates failed")

        return best_wf, best_score


_TEXT_TO_TARGET = {
    "主菜单": "main_menu", "返回主菜单": "main_menu", "返回": "main_menu",
    "main menu": "main_menu", "back": "main_menu", "home": "main_menu",
    "重试": "gameplay", "重新开始": "gameplay", "再来一次": "gameplay",
    "retry": "gameplay", "restart": "gameplay", "play again": "gameplay",
    "开始游戏": "gameplay", "start": "gameplay", "play": "gameplay",
    "开始": "gameplay", "start game": "gameplay",
    "排行榜": "leaderboard", "leaderboard": "leaderboard",
    "设置": "settings", "settings": "settings",
    "关卡选择": "level_select", "选择关卡": "level_select",
    "冒险模式": "level_select", "adventure": "level_select",
}


def _infer_button_targets(wireframe: dict) -> dict:
    """Post-process: fill missing button target_interface_id from inner_text."""
    valid_ids = {i.get("interface_id") for i in wireframe.get("interfaces", [])}

    for iface in wireframe.get("interfaces", []):
        for elem in iface.get("elements", []):
            if elem.get("type") != "button" or elem.get("event") != "click":
                continue
            if elem.get("target_interface_id") and elem["target_interface_id"] in valid_ids:
                continue
            text = (elem.get("inner_text") or "").strip().lower()
            for pattern, target in _TEXT_TO_TARGET.items():
                if pattern.lower() in text or text in pattern.lower():
                    if target in valid_ids:
                        elem["target_interface_id"] = target
                        # Also ensure navigation edges
                        iface_id = iface.get("interface_id")
                        if target not in iface.get("children", []):
                            iface.setdefault("children", []).append(target)
                        break
    return wireframe


def _validate_against_plan(wireframe: dict, plan: dict) -> dict:
    """Post-process wireframe to enforce consistency with interface plan."""
    plan_screens = {s.get("id", ""): s for s in plan.get("interfaces", [])}
    wf_screens = {s.get("interface_id", ""): s for s in wireframe.get("interfaces", [])}

    for iface in wireframe.get("interfaces", []):
        iid = iface.get("interface_id", "")
        plan_screen = plan_screens.get(iid)
        if not plan_screen:
            continue

        # Ensure children match plan's navigation_to
        plan_nav_to = plan_screen.get("navigation_to", [])
        # Map plan IDs to wireframe IDs (they should match)
        valid_targets = {t for t in plan_nav_to if t in wf_screens}
        if valid_targets:
            current_children = set(iface.get("children", []))
            iface["children"] = sorted(current_children | valid_targets)

        # Ensure parents match plan's navigation_from
        plan_nav_from = plan_screen.get("navigation_from", [])
        valid_parents = {p for p in plan_nav_from if p in wf_screens}
        if valid_parents:
            current_parents = set(iface.get("parents", []))
            iface["parents"] = sorted(current_parents | valid_parents)

    return wireframe


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
