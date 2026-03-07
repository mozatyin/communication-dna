"""Stage 4: GameCodeGenerator — PRD + Wireframe → HTML/CSS/JS game code.

Generates playable single-page HTML5 games from wireframe specs.
Each wireframe screen becomes a <div id="{interface_id}" class="screen">.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any

import anthropic

from intention_graph.game_code_quality import evaluate


_GAME_CODE_SYSTEM_PROMPT = """\
You are a game developer. Given a PRD and wireframe spec, generate a complete \
single-page HTML5 game with 3 separate files.

## Output Format

Return EXACTLY 3 fenced code blocks with these labels:

```index.html
<!-- HTML content here -->
```

```style.css
/* CSS content here */
```

```core.js
// JavaScript content here
```

## Architecture Rules

1. **Screen system**: Each wireframe `interface_id` becomes \
`<div id="{interface_id}" class="screen">`. The entry screen has \
`display:block`, all others have `display:none`.

2. **Navigation**: Implement a global `showScreen(id)` function that hides \
all screens and shows the target. Wire all wireframe navigation buttons to \
call `showScreen()`.

3. **Game canvas**: The gameplay screen uses a `<canvas>` element for rendering. \
Size it to fill the screen div.

4. **Element IDs**: Preserve ALL wireframe element IDs as HTML element IDs. \
Buttons with `target_interface_id` must call `showScreen(target)`.

5. **Styling**: CSS colors and font-sizes MUST match wireframe styles exactly. \
Use the wireframe's color values (hex codes). Layout uses CSS flexbox/grid, \
not absolute pixel positions.

6. **Game loop**: Implement via `requestAnimationFrame`. Include:
   - Game state management (menu, playing, paused, game_over)
   - Input handling appropriate for the game type
   - Score tracking and display
   - Collision detection where applicable
   - State transitions matching wireframe navigation

7. **Entry point**: The HTML file must reference `style.css` via `<link>` and \
`core.js` via `<script>`.

8. **Self-contained**: No external dependencies. Use only browser APIs.

## Quality Requirements

- Game must be immediately playable when opened in a browser
- All screens from the wireframe must be navigable
- Score display must update during gameplay
- Game over must trigger automatically on loss condition
- Retry/restart must reset game state completely
"""


class GameCodeGenerator:
    """Generate HTML5 game code from PRD + wireframe."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        kwargs: dict = {"api_key": api_key, "timeout": 600.0}
        if api_key.startswith("sk-or-"):
            kwargs["base_url"] = "https://openrouter.ai/api"
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model

    def generate(
        self,
        prd_document: str,
        wireframe: dict[str, Any],
        reference_code: str | None = None,
    ) -> dict[str, str]:
        """Generate game code files.

        Args:
            prd_document: Full PRD markdown text.
            wireframe: Wireframe JSON dict.
            reference_code: Optional reference HTML for quality guidance.

        Returns:
            Dict with keys "index.html", "style.css", "core.js".
        """
        wf_text = json.dumps(wireframe, ensure_ascii=False, indent=2)

        user_parts = [
            f"## PRD Document\n\n{prd_document}",
            f"\n## Wireframe Specification\n\n{wf_text}",
        ]

        if reference_code:
            user_parts.append(
                f"\n## Reference Code (for quality guidance)\n\n"
                f"```html\n{reference_code[:6000]}\n```\n\n"
                f"Generate code of EQUAL or BETTER quality."
            )

        user_parts.append(
            "\nGenerate the 3 game files: index.html, style.css, core.js."
        )

        chunks: list[str] = []
        with self._client.messages.stream(
            model=self._model,
            max_tokens=32000,
            temperature=0.2,
            system=_GAME_CODE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": "\n".join(user_parts)}],
        ) as stream:
            for text in stream.text_stream:
                chunks.append(text)

        raw = "".join(chunks)
        return _parse_code_response(raw)

    def generate_best_of_n(
        self,
        prd_document: str,
        wireframe: dict[str, Any],
        n: int = 3,
        reference_code: str | None = None,
    ) -> tuple[dict[str, str], float]:
        """Generate N candidates and return the best by Layer 1+2 score.

        Args:
            prd_document: Full PRD markdown text.
            wireframe: Wireframe JSON dict (also used for evaluation).
            n: Number of candidates to generate.
            reference_code: Optional reference code for guidance.

        Returns:
            Tuple of (best_code_dict, best_score).
        """
        best_code: dict[str, str] | None = None
        best_score = -1.0

        for i in range(n):
            try:
                code = self.generate(prd_document, wireframe, reference_code)
                report = evaluate(
                    code.get("index.html", ""),
                    code.get("style.css", ""),
                    code.get("core.js", ""),
                    wireframe,
                )
                score = report.overall_score
                print(
                    f"  [Best-of-{n}] Candidate {i + 1}/{n}: {score:.0%}",
                    file=sys.stderr,
                )
                if score > best_score:
                    best_score = score
                    best_code = code
            except Exception as e:
                print(
                    f"  [Best-of-{n}] Candidate {i + 1}/{n} failed: {e}",
                    file=sys.stderr,
                )
                continue

        if best_code is None:
            raise RuntimeError(f"All {n} candidates failed")

        return best_code, best_score


def _parse_code_response(raw: str) -> dict[str, str]:
    """Extract index.html, style.css, core.js from LLM response.

    Supports two formats:
    1. Labeled fenced code blocks: ```index.html ... ```
    2. FILE markers: <!-- FILE: index.html --> ... <!-- FILE: style.css -->
    """
    result = {"index.html": "", "style.css": "", "core.js": ""}

    # Strategy 1: labeled fenced code blocks
    # Match ```label or ```language label patterns
    pattern = r"```(?:html|css|javascript|js)?\s*\n?(.*?)```"
    blocks = re.findall(pattern, raw, re.DOTALL)

    if len(blocks) >= 3:
        # Try to identify which block is which by content
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

        # If we still have unassigned blocks, assign in order
        if not result["index.html"] and blocks:
            result["index.html"] = blocks[0].strip()
        if not result["style.css"] and len(blocks) > 1:
            result["style.css"] = blocks[1].strip()
        if not result["core.js"] and len(blocks) > 2:
            result["core.js"] = blocks[2].strip()
        return result

    # Strategy 2: labeled code blocks with filename in fence
    for filename in result:
        # Match ```filename or ```{ext} filename
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
