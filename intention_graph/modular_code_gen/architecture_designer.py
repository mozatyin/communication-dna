"""Architecture Designer: generate ArchitectureDoc from ModuleSpecs."""

from __future__ import annotations

import json
import time
from typing import Any

import anthropic

from intention_graph.modular_code_gen.models import (
    ArchitectureDoc,
    EventDef,
    FieldDef,
    FunctionSig,
    InteractionRule,
    ModuleInterface,
    ModuleSpec,
    ParamDef,
    SharedDataStructure,
    StateMachine,
    StateTransition,
)


_SYSTEM_PROMPT = """\
You are a game software architect. Given a PRD, wireframe, and list of \
module specs, design a complete technical architecture that allows each \
module to be implemented independently.

This is the MOST CRITICAL document — it defines the contract all module \
generators will follow. Each module developer sees ONLY this architecture \
doc and their own module interface. They cannot see other modules' code.

## What You Must Define

### 1. state_machine — Game State Lifecycle (CRITICAL)
Define ALL game states and valid transitions. Every module needs this to \
know when to activate. Example states: menu, playing, paused, game_over.
- Each transition has: from_state, to_state, trigger (event name), triggered_by (module_id)
- Every state must be reachable from the initial state
- game_over must transition back to playing (retry) and/or menu

### 2. shared_data — Data Ownership
Concrete SharedDataStructure entries (GameState with ALL fields). \
For EACH field, specify:
- **writers**: which module_ids can MODIFY this field
- **readers**: which module_ids READ this field
- Only ONE module should write each field (single-writer principle). \
The game_state module may write fields during init/reset.

### 3. events — Communication Protocol
Event bus protocol — event names, payload schemas, producers, consumers. \
Events are how modules communicate without direct imports. \
Include state transition events (e.g., GAME_OVER, GAME_START).

### 4. interactions — Collision/Interaction Rules
For games with moving objects, define what interacts with what:
- subject: the checking object type (e.g., "bullet")
- object: what it interacts with (e.g., "enemy")
- condition: detection method (e.g., "bounding box overlap")
- effect: what happens (e.g., "destroy both, emit ENEMY_DESTROYED, add 10 to score")
- module: which module_id is responsible for this detection

### 5. modules — Interface Contracts
For EVERY input module, define a ModuleInterface with:
- exports: Function signatures with:
  - name, params (with types), return type
  - **precondition**: what must be true before calling (e.g., "GameState.gameStatus === 'playing'")
  - **postcondition**: what is guaranteed after (e.g., "all bullet positions updated")
  - **description**: what the function does
- imports: Which other module_ids this module depends on
- state_access: Which SharedDataStructure names this module reads/writes
- update_function: Name of the function called each frame (or null)
- render_function: Name of the function called each render (or null)

### 6. Execution Orders
- **init_order**: game_state FIRST, then systems, renderer LAST
- **update_order**: Order for per-frame update calls (input→physics→collision→scoring)
- **render_order**: Order for per-frame render calls (background→objects→UI)

## Rules

- All function params use only primitive types (number, string, boolean) + \
shared structure names
- Each module with game-loop participation MUST have update_function and/or \
render_function
- All module_ids referenced in init/update/render_order must exist in modules
- Every module must have at least one export
- Event producers/consumers must reference known module_ids
- game_state module must always be first in init_order
- update_order should reflect logical dependency: input processing before \
physics, physics before collision, collision before scoring

## Output

Return ONLY valid JSON matching this structure:
{
  "game_title": "...",
  "state_machine": {
    "states": ["menu", "playing", "paused", "game_over"],
    "initial": "menu",
    "transitions": [
      {"from_state": "menu", "to_state": "playing", "trigger": "GAME_START", "triggered_by": "game_state"},
      {"from_state": "playing", "to_state": "game_over", "trigger": "PLAYER_DIED", "triggered_by": "..."},
      {"from_state": "game_over", "to_state": "playing", "trigger": "RETRY", "triggered_by": "game_state"},
      {"from_state": "game_over", "to_state": "menu", "trigger": "RETURN_MENU", "triggered_by": "game_state"}
    ]
  },
  "modules": [
    {
      "module_id": "...",
      "description": "...",
      "exports": [{"name": "init", "params": [], "returns": "void",
                    "precondition": "", "postcondition": "module state initialized",
                    "description": "Initialize module"}],
      "imports": ["..."],
      "state_access": ["GameState"],
      "update_function": "update",
      "render_function": "render"
    }
  ],
  "shared_data": [
    {
      "name": "GameState",
      "fields": [
        {"name": "score", "type": "number", "default": "0",
         "writers": ["score_system"], "readers": ["ui_renderer"]},
        {"name": "gameStatus", "type": "string", "default": "menu",
         "writers": ["game_state"], "readers": ["ALL"]}
      ],
      "description": "Core game state shared across all modules"
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
  "interactions": [
    {
      "subject": "bullet",
      "object": "enemy",
      "condition": "bounding box overlap",
      "effect": "destroy both, emit ENEMY_DESTROYED with points",
      "module": "shooting"
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
            raw_params = e.get("params", [])
            params = []
            for p in raw_params:
                if isinstance(p, dict):
                    params.append(ParamDef(**p))
                elif isinstance(p, str):
                    params.append(ParamDef(name=p, type="any"))
            exports.append(FunctionSig(
                name=e["name"],
                params=params,
                returns=e.get("returns", "void"),
                description=e.get("description", ""),
                precondition=e.get("precondition", ""),
                postcondition=e.get("postcondition", ""),
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
        fields = [
            FieldDef(
                name=f["name"],
                type=f["type"],
                default=f.get("default", ""),
                writers=f.get("writers", []),
                readers=f.get("readers", []),
            )
            for f in sd.get("fields", [])
        ]
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

    # Parse state machine
    state_machine = None
    sm_data = data.get("state_machine")
    if sm_data:
        transitions = [
            StateTransition(
                from_state=t.get("from_state", t.get("from", "")),
                to_state=t.get("to_state", t.get("to", "")),
                trigger=t.get("trigger", ""),
                triggered_by=t.get("triggered_by", ""),
            )
            for t in sm_data.get("transitions", [])
        ]
        state_machine = StateMachine(
            states=sm_data.get("states", []),
            initial=sm_data.get("initial", "menu"),
            transitions=transitions,
        )

    # Parse interaction rules
    interactions = [
        InteractionRule(
            subject=ir["subject"],
            object=ir["object"],
            condition=ir.get("condition", ""),
            effect=ir.get("effect", ""),
            module=ir.get("module", ""),
        )
        for ir in data.get("interactions", [])
    ]

    return ArchitectureDoc(
        game_title=data.get("game_title", "Unknown"),
        modules=modules,
        shared_data=shared_data,
        events=events,
        init_order=data.get("init_order", []),
        update_order=data.get("update_order", []),
        render_order=data.get("render_order", []),
        global_constants=data.get("global_constants", {}),
        state_machine=state_machine,
        interactions=interactions,
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

        raw = self._call_with_retry(user_msg)
        data = _parse_json(raw)
        if not data:
            raise ValueError("Failed to parse architecture from LLM response")

        arch = _parse_architecture(data)

        # Post-validation
        self._post_validate(arch, modules)

        return arch

    def _call_with_retry(self, user_msg: str) -> str:
        """LLM call with retry on rate limit errors."""
        for attempt in range(3):
            try:
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=8192,
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
        raise RuntimeError("Architecture design LLM call failed after 3 retries")

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
