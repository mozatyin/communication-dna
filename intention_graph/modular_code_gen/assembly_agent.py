"""Assembly Agent: wire modules together into index.html + style.css + core.js."""

from __future__ import annotations

import json
import re
import time
from typing import Any

import anthropic

from intention_graph.modular_code_gen.models import ArchitectureDoc, ModuleCode


_SYSTEM_PROMPT = """\
You are a game integration engineer. You receive pre-written module code and \
an architecture document. Your job is to WIRE THEM TOGETHER into a working \
single-page HTML5 game.

## Output Format

Return EXACTLY 3 fenced code blocks:

```index.html
<!-- HTML here -->
```

```style.css
/* CSS here */
```

```core.js
// JavaScript here
```

## What You Must Create

### index.html
- Screen divs from wireframe (each with `class="screen"`)
- Entry screen has `display:block`, others have `display:none`
- Canvas element in gameplay screen
- `<link>` to style.css, `<script>` for core.js

### style.css
- Wireframe-matching styles (colors, fonts, layout)
- Screen transition styles (display:none/block)
- Responsive layout using flexbox/grid

### core.js
Build this in order:

1. **EventBus**:
```javascript
const EventBus = {
    _handlers: {},
    on(event, fn) {
        (this._handlers[event] = this._handlers[event] || []).push(fn);
    },
    emit(event, data) {
        (this._handlers[event] || []).forEach(fn => fn(data));
    }
};
```

2. **Shared state objects** matching ArchitectureDoc SharedDataStructure definitions

3. **Concatenated module code** (copy each module's code exactly as provided)

4. **showScreen(id)** function — hides all screens, shows target

5. **Game loop**:
```javascript
function gameLoop(timestamp) {
    const dt = (timestamp - lastTime) / 1000;
    lastTime = timestamp;
    // Call update functions in update_order
    // Call render functions in render_order
    if (GameState.gameStatus === 'playing') {
        requestAnimationFrame(gameLoop);
    }
}
```

6. **Module initialization** in init_order sequence

7. **State transitions** — implement functions for each transition in the \
state_machine (e.g., startGame, gameOver, retry). Each transition function:
   - Updates GameState.gameStatus to the target state
   - Emits the trigger event via EventBus
   - Calls showScreen() for the corresponding screen

8. **Input handlers** (keyboard, mouse, touch as appropriate)

9. **Screen navigation** wired to wireframe buttons

## CRITICAL Rules

- Do NOT rewrite module logic — use the provided code as-is
- Wire modules together through the EventBus and shared state
- showScreen() must set display:none on all .screen divs, then display:block on target
- All wireframe element IDs must appear in HTML
- Colors/fonts must match wireframe styles EXACTLY (copy hex codes from wireframe)
- Game must be immediately playable when opened

## CSS Quality (HIGH PRIORITY)

The CSS must faithfully reproduce the wireframe's visual design:
- Copy ALL color hex codes from wireframe styles into CSS
- Match font sizes from wireframe (convert to rem/px as appropriate)
- Use wireframe background-color values for buttons and containers
- Every wireframe element with a style must have a corresponding CSS rule
- Responsive layout: use flexbox/grid, not absolute positioning

## Mobile Support

- Add `<meta name="viewport" content="width=device-width, initial-scale=1.0">` to HTML
- Add touch event listeners (touchstart/touchmove/touchend) alongside keyboard handlers
- Buttons must have `cursor: pointer` and hover states in CSS

## High Score Persistence

- Use localStorage to save/load high scores on game over
- Display best score on game over screen
- Populate leaderboard screen with top 5 scores from localStorage
"""


def _parse_code_response(raw: str) -> dict[str, str]:
    """Extract index.html, style.css, core.js from LLM response.

    Reuses the same parsing logic as game_code_generator.py.
    """
    result = {"index.html": "", "style.css": "", "core.js": ""}

    pattern = r"```(?:html|css|javascript|js)?\s*\n?(.*?)```"
    blocks = re.findall(pattern, raw, re.DOTALL)

    if len(blocks) >= 3:
        for block in blocks:
            block = block.strip()
            if "<html" in block.lower() or "<!doctype" in block.lower():
                result["index.html"] = block
            elif re.search(r"[{};]\s*\n", block) and not re.search(
                r"\bfunction\b|\bconst\b|\blet\b|\bvar\b", block
            ):
                result["style.css"] = block
            elif re.search(
                r"\bfunction\b|\bconst\b|\blet\b|\bvar\b|\bdocument\b", block
            ):
                if not result["core.js"]:
                    result["core.js"] = block

        if not result["index.html"] and blocks:
            result["index.html"] = blocks[0].strip()
        if not result["style.css"] and len(blocks) > 1:
            result["style.css"] = blocks[1].strip()
        if not result["core.js"] and len(blocks) > 2:
            result["core.js"] = blocks[2].strip()
        return result

    for filename in result:
        name_escaped = re.escape(filename)
        ext = filename.rsplit(".", 1)[-1]
        patterns = [
            rf"```{name_escaped}\s*\n(.*?)```",
            rf"```{ext}\s+{name_escaped}\s*\n(.*?)```",
            rf"<!--\s*FILE:\s*{name_escaped}\s*-->\s*\n(.*?)(?=<!--\s*FILE:|$)",
        ]
        for p in patterns:
            match = re.search(p, raw, re.DOTALL | re.IGNORECASE)
            if match:
                result[filename] = match.group(1).strip()
                break

    return result


class AssemblyAgent:
    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
    ):
        kwargs: dict[str, Any] = {"api_key": api_key, "timeout": 600.0}
        if api_key.startswith("sk-or-"):
            kwargs["base_url"] = "https://openrouter.ai/api"
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model

    def assemble(
        self,
        modules: list[ModuleCode],
        architecture: ArchitectureDoc,
        wireframe: dict,
        prd_document: str,
    ) -> dict[str, str]:
        """Assemble modules into index.html + style.css + core.js."""
        arch_json = architecture.model_dump_json(indent=2)
        wf_text = json.dumps(wireframe, ensure_ascii=False, indent=2)

        module_code_sections = []
        for mc in modules:
            stub_note = " (STUB — implement no-op)" if mc.is_stub else ""
            module_code_sections.append(
                f"### Module: {mc.module_id}{stub_note}\n```javascript\n{mc.js_code}\n```"
            )
        modules_text = "\n\n".join(module_code_sections)

        # Extract wireframe styles for CSS emphasis
        style_summary = self._extract_wireframe_styles(wireframe)

        user_msg = (
            f"## Architecture Document\n{arch_json}\n\n"
            f"## Wireframe\n{wf_text[:8000]}\n\n"
            f"## Wireframe Style Reference (MUST match in CSS)\n{style_summary}\n\n"
            f"## PRD\n{prd_document[:3000]}\n\n"
            f"## Module Code\n{modules_text}\n\n"
            "Assemble these modules into a working game. "
            "IMPORTANT: CSS must match ALL wireframe colors and font sizes exactly. "
            "Return index.html, style.css, and core.js."
        )

        raw = self._call_llm_with_retry(user_msg)
        return _parse_code_response(raw)

    @staticmethod
    def _extract_wireframe_styles(wireframe: dict) -> str:
        """Extract all styles from wireframe elements for CSS reference."""
        lines = []
        for screen in wireframe.get("interfaces", []):
            sid = screen.get("interface_id", "?")
            for elem in screen.get("elements", []):
                eid = elem.get("id", "?")
                style = elem.get("style", {})
                if style:
                    props = "; ".join(f"{k}: {v}" for k, v in style.items() if v)
                    if props:
                        lines.append(f"#{eid} (in {sid}): {props}")
        return "\n".join(lines) if lines else "No explicit styles in wireframe."

    def _call_llm_with_retry(self, user_msg: str) -> str:
        """Stream LLM call with retry on rate limit errors."""
        for attempt in range(3):
            try:
                chunks: list[str] = []
                with self._client.messages.stream(
                    model=self._model,
                    max_tokens=32000,
                    temperature=0.2,
                    system=_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_msg}],
                ) as stream:
                    for text in stream.text_stream:
                        chunks.append(text)
                return "".join(chunks)
            except anthropic.RateLimitError:
                wait = (attempt + 1) * 10
                time.sleep(wait)
            except anthropic.APIStatusError as e:
                if e.status_code in (403, 429, 529):
                    wait = (attempt + 1) * 10
                    time.sleep(wait)
                else:
                    raise
        raise RuntimeError("Assembly LLM call failed after 3 retries")
