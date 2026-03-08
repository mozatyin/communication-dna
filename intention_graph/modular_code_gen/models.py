"""Pydantic models for modular code generation pipeline."""

from __future__ import annotations

from pydantic import BaseModel, model_validator


class FieldDef(BaseModel):
    name: str
    type: str
    default: str = ""
    writers: list[str] = []  # module_ids that write this field
    readers: list[str] = []  # module_ids that read this field


class SharedDataStructure(BaseModel):
    name: str
    fields: list[FieldDef]
    description: str = ""


class StateTransition(BaseModel):
    from_state: str
    to_state: str
    trigger: str  # event name or action that causes transition
    triggered_by: str = ""  # module_id responsible


class StateMachine(BaseModel):
    states: list[str]
    initial: str
    transitions: list[StateTransition]


class EventDef(BaseModel):
    name: str
    payload: dict[str, str]
    producers: list[str]
    consumers: list[str]


class ParamDef(BaseModel):
    name: str
    type: str


class FunctionSig(BaseModel):
    name: str
    params: list[ParamDef]
    returns: str = "void"
    description: str = ""
    precondition: str = ""  # what must be true before calling
    postcondition: str = ""  # what is guaranteed after calling


class InteractionRule(BaseModel):
    subject: str  # e.g. "bullet"
    object: str  # e.g. "enemy"
    condition: str  # e.g. "bounding box overlap"
    effect: str  # e.g. "destroy both, emit ENEMY_DESTROYED"
    module: str  # module_id responsible for detection


class ModuleSpec(BaseModel):
    module_id: str
    description: str
    core_systems: list[str]
    dependencies: list[str]


class ModuleInterface(BaseModel):
    module_id: str
    description: str
    exports: list[FunctionSig]
    imports: list[str]
    state_access: list[str]
    update_function: str | None = None
    render_function: str | None = None


class ArchitectureDoc(BaseModel):
    game_title: str
    modules: list[ModuleInterface]
    shared_data: list[SharedDataStructure]
    events: list[EventDef]
    init_order: list[str]
    update_order: list[str]
    render_order: list[str]
    global_constants: dict[str, str] = {}
    state_machine: StateMachine | None = None
    interactions: list[InteractionRule] = []

    @model_validator(mode="after")
    def _validate_order_refs(self) -> ArchitectureDoc:
        module_ids = {m.module_id for m in self.modules}
        for order_name in ("init_order", "update_order", "render_order"):
            for mid in getattr(self, order_name):
                if mid not in module_ids:
                    raise ValueError(
                        f"{order_name} references unknown module '{mid}'. "
                        f"Known: {sorted(module_ids)}"
                    )
        return self


class ModuleCode(BaseModel):
    module_id: str
    js_code: str
    is_stub: bool = False


class AssembledCode(BaseModel):
    html: str
    css: str
    js: str
