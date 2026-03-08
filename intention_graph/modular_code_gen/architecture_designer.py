"""Architecture Designer: generate ArchitectureDoc from ModuleSpecs."""

from __future__ import annotations

import json
from typing import Any

import anthropic

from intention_graph.modular_code_gen.models import (
    ArchitectureDoc,
    EventDef,
    FieldDef,
    FunctionSig,
    ModuleInterface,
    ModuleSpec,
    ParamDef,
    SharedDataStructure,
)


_SYSTEM_PROMPT = """\
You are a game software architect. Given a PRD, wireframe, and list of \
module specs, design a complete technical architecture that allows each \
module to be implemented independently.

This is the MOST CRITICAL document — it defines the contract all module \
generators will follow.

## What You Must Define

1. **shared_data**: Concrete SharedDataStructure entries (GameState with ALL fields, \
PlayerState, etc.). Each field has name, type, and default value.

2. **events**: Event bus protocol — event names, payload schemas, producers, consumers. \
Events are how modules communicate without direct imports.

3. **modules**: For EVERY input module, define a ModuleInterface with:
   - exports: Concrete function signatures (name, params with types, return type)
   - imports: Which other module_ids this module depends on
   - state_access: Which SharedDataStructure names this module reads/writes
   - update_function: Name of the function called each frame (or null)
   - render_function: Name of the function called each render (or null)

4. **init_order**: game_state FIRST, then systems, renderer LAST
5. **update_order**: Order for per-frame update calls
6. **render_order**: Order for per-frame render calls

## Rules

- All function params use only primitive types (number, string, boolean) + \
shared structure names
- Each module with game-loop participation MUST have update_function and/or \
render_function
- All module_ids referenced in init/update/render_order must exist in modules
- Every module must have at least one export
- Event producers/consumers must reference known module_ids
- game_state module must always be first in init_order

## Output

Return ONLY valid JSON matching this structure:
{
  "game_title": "...",
  "modules": [
    {
      "module_id": "...",
      "description": "...",
      "exports": [{"name": "init", "params": [], "returns": "void", "description": "..."}],
      "imports": ["..."],
      "state_access": ["GameState"],
      "update_function": "update",
      "render_function": "render"
    }
  ],
  "shared_data": [
    {
      "name": "GameState",
      "fields": [{"name": "score", "type": "number", "default": "0"}],
      "description": "..."
    }
  ],
  "events": [
    {
      "name": "ENEMY_DESTROYED",
      "payload": {"enemyId": "string", "points": "number"},
      "producers": ["shooting"],
      "consumers": ["game_state"]
    }
  ],
  "init_order": ["game_state", "..."],
  "update_order": ["...", "..."],
  "render_order": ["...", "..."],
  "global_constants": {"CANVAS_WIDTH": "1080", "CANVAS_HEIGHT": "1920"}
}
"""


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


def _parse_architecture(data: dict) -> ArchitectureDoc:
    """Parse raw JSON dict into ArchitectureDoc with nested model construction."""
    modules = []
    for m in data.get("modules", []):
        exports = []
        for e in m.get("exports", []):
            params = [ParamDef(**p) for p in e.get("params", [])]
            exports.append(FunctionSig(
                name=e["name"],
                params=params,
                returns=e.get("returns", "void"),
                description=e.get("description", ""),
            ))
        modules.append(ModuleInterface(
            module_id=m["module_id"],
            description=m.get("description", ""),
            exports=exports,
            imports=m.get("imports", []),
            state_access=m.get("state_access", []),
            update_function=m.get("update_function"),
            render_function=m.get("render_function"),
        ))

    shared_data = []
    for sd in data.get("shared_data", []):
        fields = [FieldDef(**f) for f in sd.get("fields", [])]
        shared_data.append(SharedDataStructure(
            name=sd["name"],
            fields=fields,
            description=sd.get("description", ""),
        ))

    events = []
    for ev in data.get("events", []):
        events.append(EventDef(
            name=ev["name"],
            payload=ev.get("payload", {}),
            producers=ev.get("producers", []),
            consumers=ev.get("consumers", []),
        ))

    return ArchitectureDoc(
        game_title=data.get("game_title", "Unknown"),
        modules=modules,
        shared_data=shared_data,
        events=events,
        init_order=data.get("init_order", []),
        update_order=data.get("update_order", []),
        render_order=data.get("render_order", []),
        global_constants=data.get("global_constants", {}),
    )


class ArchitectureDesigner:
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

    def design(
        self,
        prd_document: str,
        wireframe: dict,
        modules: list[ModuleSpec],
    ) -> ArchitectureDoc:
        """Design architecture from PRD + wireframe + module specs."""
        modules_text = json.dumps(
            [m.model_dump() for m in modules], ensure_ascii=False, indent=2
        )
        wf_summary = json.dumps(
            [
                {
                    "id": i.get("interface_id"),
                    "name": i.get("interface_name"),
                    "type": i.get("type"),
                    "children": i.get("children", []),
                    "elements": len(i.get("elements", [])),
                }
                for i in wireframe.get("interfaces", [])
            ],
            ensure_ascii=False,
            indent=2,
        )

        user_msg = (
            f"## PRD\n{prd_document[:5000]}\n\n"
            f"## Wireframe Screens\n{wf_summary}\n\n"
            f"## Module Specs\n{modules_text}\n\n"
            "Design the complete architecture JSON."
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=8192,
            temperature=0.0,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )

        raw = response.content[0].text
        data = _parse_json(raw)
        if not data:
            raise ValueError("Failed to parse architecture from LLM response")

        arch = _parse_architecture(data)

        # Post-validation
        self._post_validate(arch, modules)

        return arch

    def _post_validate(
        self, arch: ArchitectureDoc, input_specs: list[ModuleSpec]
    ) -> None:
        """Validate architecture consistency after parsing."""
        arch_module_ids = {m.module_id for m in arch.modules}
        input_module_ids = {s.module_id for s in input_specs}

        # All input modules should appear in architecture
        missing = input_module_ids - arch_module_ids
        if missing:
            raise ValueError(
                f"Architecture missing modules from input: {sorted(missing)}"
            )

        # Event producers/consumers reference known modules
        for event in arch.events:
            for mid in event.producers + event.consumers:
                if mid not in arch_module_ids:
                    raise ValueError(
                        f"Event '{event.name}' references unknown module '{mid}'"
                    )

        # Every module has at least one export
        for m in arch.modules:
            if not m.exports:
                raise ValueError(
                    f"Module '{m.module_id}' has no exports"
                )
