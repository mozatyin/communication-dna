"""Module Generator: parallel code generation for each module."""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import anthropic

from intention_graph.modular_code_gen.models import (
    ArchitectureDoc,
    ModuleCode,
    ModuleInterface,
)
from intention_graph.modular_code_gen.module_validator import validate_module


_SYSTEM_PROMPT = """\
You are a game module programmer. You will receive an architecture document \
and ONE module interface to implement. Generate ONLY the JavaScript code for \
this specific module.

## Rules

1. Export EXACTLY the functions listed in your module's exports — no more, no less.
2. Use shared data structures by reference (assume they exist in global scope).
3. Emit/listen for ONLY events listed in the architecture's event catalog.
4. Wrap ALL code in an IIFE namespace pattern:
   ```
   const ModuleName = (function() {
       // private state and functions
       function init() { ... }
       function update(dt) { ... }
       function render(ctx) { ... }
       return { init, update, render };
   })();
   ```
5. Do NOT create global variables outside the IIFE.
6. Do NOT import or reference other modules' internal code — only use their \
   exported functions as documented in the architecture.
7. Implement complete, working game logic — not stubs or placeholders.

## Architecture Guidance

- **State Machine**: Check `state_machine` in the architecture. Your update/render \
functions should respect `GameState.gameStatus` — only run game logic when status \
matches your function's precondition (usually "playing").
- **Data Ownership**: Check `writers`/`readers` on shared_data fields. Only WRITE \
to fields where your module_id is listed as a writer. You may READ any field listed \
in your state_access.
- **Function Contracts**: Each export has a precondition and postcondition. \
Ensure your implementation satisfies the postcondition when the precondition holds.
- **Interactions**: If your module owns an interaction rule, implement the collision \
detection described in the `condition` field and the `effect` when triggered.

## Output

Return ONLY the JavaScript code for this module. No markdown fences, no \
explanations — just the raw JavaScript.
"""


def _to_camel(snake: str) -> str:
    """Convert snake_case to CamelCase."""
    return "".join(word.capitalize() for word in snake.split("_"))


def _create_stub(interface: ModuleInterface) -> ModuleCode:
    """Create a stub module with no-op exports."""
    exports = ", ".join(
        f"{fn.name}: function() {{}}" for fn in interface.exports
    )
    camel = _to_camel(interface.module_id)
    return ModuleCode(
        module_id=interface.module_id,
        js_code=(
            f"const {camel} = (function() {{ return {{ {exports} }}; }})();"
        ),
        is_stub=True,
    )


def _strip_fences(raw: str) -> str:
    """Remove markdown code fences if present."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
    return raw.strip()


class ModuleGenerator:
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

    def generate_module(
        self,
        architecture: ArchitectureDoc,
        module: ModuleInterface,
        prd_document: str,
        wireframe: dict,
    ) -> ModuleCode:
        """Generate code for a single module with retry on validation failure."""
        arch_json = architecture.model_dump_json(indent=2)

        module_json = json.dumps(module.model_dump(), indent=2, ensure_ascii=False)

        user_msg = (
            f"## Architecture Document\n{arch_json}\n\n"
            f"## Your Module Interface\n{module_json}\n\n"
            f"## PRD (for context)\n{prd_document[:3000]}\n\n"
            f"Generate the JavaScript code for module '{module.module_id}'."
        )

        # First attempt
        code = self._call_llm(user_msg)
        result = validate_module(code, module)
        if result.is_valid:
            return code

        # Retry with error feedback
        retry_msg = (
            f"The code you generated has issues:\n"
            + "\n".join(f"- {issue}" for issue in result.issues)
            + "\n\nFix these issues and return the corrected JavaScript code."
        )
        code = self._call_llm(user_msg + "\n\n" + retry_msg)
        result = validate_module(code, module)
        if result.is_valid:
            return code

        # Total failure: return stub
        return _create_stub(module)

    def generate_all_parallel(
        self,
        architecture: ArchitectureDoc,
        prd_document: str,
        wireframe: dict,
        max_workers: int = 4,
    ) -> list[ModuleCode]:
        """Generate code for all modules in parallel."""
        results: dict[str, ModuleCode] = {}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self.generate_module,
                    architecture,
                    module,
                    prd_document,
                    wireframe,
                ): module.module_id
                for module in architecture.modules
            }
            for future in as_completed(futures):
                module_id = futures[future]
                try:
                    results[module_id] = future.result()
                except Exception:
                    # Find the interface and create a stub
                    for m in architecture.modules:
                        if m.module_id == module_id:
                            results[module_id] = _create_stub(m)
                            break

        # Return in init_order
        ordered = []
        for mid in architecture.init_order:
            if mid in results:
                ordered.append(results.pop(mid))
        # Append any remaining (not in init_order)
        ordered.extend(results.values())
        return ordered

    def _call_llm(self, user_msg: str) -> ModuleCode:
        """Make a single LLM call and return ModuleCode."""
        response = self._client.messages.create(
            model=self._model,
            max_tokens=16000,
            temperature=0.2,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = _strip_fences(response.content[0].text)

        # Extract module_id from the code
        match = re.search(r"const\s+(\w+)\s*=\s*\(function", raw)
        module_id = match.group(1) if match else "unknown"
        # Try to reverse CamelCase to snake_case
        snake = re.sub(r"(?<!^)(?=[A-Z])", "_", module_id).lower()

        return ModuleCode(module_id=snake, js_code=raw)
