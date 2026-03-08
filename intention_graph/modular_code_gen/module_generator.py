"""Module Generator: parallel code generation for each module."""

from __future__ import annotations

import json
import re
import time
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

# ── Domain-specific implementation guides ─────────────────────────────────

_DOMAIN_PHYSICS = """\

## Domain: Physics-Based Game

Your module likely deals with moving objects. Implementation requirements:

### Collision Detection
- Use bounding-box overlap: `(ax < bx+bw && ax+aw > bx && ay < by+bh && ay+ah > by)`
- Add 1-2px tolerance margin for better feel
- Check EVERY frame in update(), not just on events

### Movement & Physics
- Use velocity vectors: `obj.x += obj.vx * dt; obj.y += obj.vy * dt`
- Apply gravity as acceleration: `obj.vy += GRAVITY * dt`
- Bounce: reverse velocity component and multiply by restitution (0.8-1.0)
- Clamp positions to canvas bounds after movement

### Paddle/Player Deflection
- Deflection angle based on hit position: `angle = (hitX - paddleCenterX) / paddleHalfWidth * maxAngle`
- Convert angle to velocity: `vx = speed * Math.sin(angle); vy = -speed * Math.cos(angle)`

### Rendering
- Clear canvas with `ctx.clearRect(0, 0, canvas.width, canvas.height)` each frame
- Draw each object with distinct `ctx.fillStyle` color
- Draw score/HUD with `ctx.fillText()`
"""

_DOMAIN_GRID = """\

## Domain: Grid-Based Game

Your module likely manages a grid/board. Implementation requirements:

### Grid System
- Store grid as 2D array: `grid[row][col]`
- Convert pixel↔grid: `col = Math.floor(pixelX / cellSize); row = Math.floor(pixelY / cellSize)`
- Draw cells: `ctx.fillRect(col * cellSize, row * cellSize, cellSize - gap, cellSize - gap)`

### Grid Operations
- Check bounds before access: `if (row >= 0 && row < rows && col >= 0 && col < cols)`
- For flood fill (minesweeper, mine reveal): use BFS queue, not recursion
  ```
  const queue = [[startRow, startCol]];
  while (queue.length > 0) {
      const [r, c] = queue.shift();
      // process cell, add neighbors if condition met
  }
  ```

### Match Detection (Match-3, 2048)
- Scan rows then columns for 3+ consecutive same-type tiles
- After removing matches, apply gravity (shift tiles down, fill empty from top)
- Re-scan for cascading matches until no new matches found

### Tile Merging (2048)
- Process each row/column as 1D array in swipe direction
- Compact non-zero values, merge adjacent equals, compact again
- Track if any tile moved to determine valid move
"""

_DOMAIN_PIECE = """\

## Domain: Piece/Block Game (Tetris-like)

Your module likely handles falling pieces. Implementation requirements:

### Piece Definitions
- Define all pieces as 2D arrays of coordinates relative to pivot
- Store all 4 rotation states, or compute rotation:
  `rotated[r][c] = original[cols-1-c][r]`

### Piece Movement
- Move: translate all block positions by delta
- Rotate: apply rotation matrix, check collision, wall-kick if needed
- Drop: move down until collision, then lock piece to grid
- Gravity: auto-drop every N frames (decrease N for speed increase)

### Collision Detection
- For each block in piece, check: within bounds AND grid cell is empty
- Wall kick: if rotation collides, try shifting left/right by 1-2 cells

### Line Clear
- After locking piece: scan all rows from bottom
- Full row = all cells filled → remove row, shift above rows down
- Award points per lines cleared (1=100, 2=300, 3=500, 4=800)
"""

_DOMAIN_ACTION = """\

## Domain: Action Game (Shooter/Runner)

Your module likely handles player, enemies, or projectiles. Implementation requirements:

### Player Movement
- Smooth movement: track velocity, apply acceleration, cap at max speed
- Boundary clamping: `player.x = Math.max(0, Math.min(canvasW - player.w, player.x))`
- Input: set velocity flags on keydown/keyup, apply in update()

### Projectile System
- Store bullets as array of {x, y, vx, vy, active}
- In update: move all bullets, remove off-screen ones
- Fire rate: track lastFireTime, enforce cooldown
- Collision with enemies: iterate both arrays, check overlap

### Enemy System
- Spawn enemies at intervals: `if (now - lastSpawn > spawnInterval) { ... }`
- Move patterns: straight-line, sine-wave, or toward player
- Increase difficulty over time: faster spawn rate, faster movement

### Rendering
- Layer order: background → enemies → bullets → player → HUD
- Use distinct colors for player (green), enemies (red), bullets (yellow)
- Draw health/lives as icons or text
"""

_DOMAIN_PUZZLE = """\

## Domain: Puzzle/Logic Game

Your module likely handles board state and logic. Implementation requirements:

### Board Rendering
- Draw grid lines, then cell contents on top
- Use distinct colors per cell state/value (define a color map)
- Highlight selected/active cells with border or background

### Input Handling
- Canvas click → grid coordinate: `col = Math.floor((e.offsetX - gridOffsetX) / cellSize)`
- For swipe: track touchstart position, calculate delta on touchend
  `dx = endX - startX; dy = endY - startY`
  Direction = largest absolute component: `if (Math.abs(dx) > Math.abs(dy)) { horizontal }`

### State Validation
- Before applying move: check if it's legal (would result in valid state change)
- After applying move: check win condition AND game over condition
- If no valid moves remain → game over

### Score & Leaderboard
- Track score in shared state, update display each frame
- On game over: save to localStorage
  ```
  const scores = JSON.parse(localStorage.getItem('scores') || '[]');
  scores.push({score, date: Date.now()});
  scores.sort((a,b) => b.score - a.score);
  localStorage.setItem('scores', JSON.stringify(scores.slice(0, 10)));
  ```
"""

# Map game keywords to domain prompts
_DOMAIN_KEYWORDS: dict[str, str] = {
    # Physics-based
    "flappy": _DOMAIN_PHYSICS,
    "breakout": _DOMAIN_PHYSICS,
    "pinball": _DOMAIN_PHYSICS,
    "pong": _DOMAIN_PHYSICS,
    # Grid-based
    "minesweeper": _DOMAIN_GRID,
    "match3": _DOMAIN_GRID,
    "match 3": _DOMAIN_GRID,
    "2048": _DOMAIN_GRID,
    "sudoku": _DOMAIN_GRID,
    "sokoban": _DOMAIN_GRID,
    # Piece/block
    "tetris": _DOMAIN_PIECE,
    "block": _DOMAIN_PIECE,
    # Action
    "shooter": _DOMAIN_ACTION,
    "space": _DOMAIN_ACTION,
    "runner": _DOMAIN_ACTION,
    "ninja": _DOMAIN_ACTION,
    "whack": _DOMAIN_ACTION,
    # Puzzle (fallback for grid-ish games)
    "puzzle": _DOMAIN_PUZZLE,
    "snake": _DOMAIN_PUZZLE,
    "popstar": _DOMAIN_PUZZLE,
}


def _detect_domain(game_title: str, prd_document: str) -> str:
    """Detect game domain from title and PRD, return domain-specific prompt."""
    text = (game_title + " " + prd_document[:500]).lower()
    for keyword, prompt in _DOMAIN_KEYWORDS.items():
        if keyword in text:
            return prompt
    return ""  # No domain-specific guidance


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

        # Detect domain and add specific guidance
        domain_prompt = _detect_domain(architecture.game_title, prd_document)

        user_msg = (
            f"## Architecture Document\n{arch_json}\n\n"
            f"## Your Module Interface\n{module_json}\n\n"
            f"## PRD (for context)\n{prd_document[:3000]}\n\n"
            f"{domain_prompt}\n\n"
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
        max_workers: int = 2,
    ) -> list[ModuleCode]:
        """Generate code for all modules in parallel with staggered launches."""
        results: dict[str, ModuleCode] = {}

        def _generate_with_delay(module: ModuleInterface, delay: float) -> ModuleCode:
            if delay > 0:
                time.sleep(delay)
            return self.generate_module(architecture, module, prd_document, wireframe)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for i, module in enumerate(architecture.modules):
                # Stagger launches by 2s to avoid rate limits
                delay = i * 2.0
                future = executor.submit(_generate_with_delay, module, delay)
                futures[future] = module.module_id

            for future in as_completed(futures):
                module_id = futures[future]
                try:
                    results[module_id] = future.result()
                except Exception:
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
        """Make a single LLM call with retry on rate limit errors."""
        for attempt in range(3):
            try:
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
                snake = re.sub(r"(?<!^)(?=[A-Z])", "_", module_id).lower()

                return ModuleCode(module_id=snake, js_code=raw)
            except anthropic.RateLimitError:
                wait = (attempt + 1) * 10
                time.sleep(wait)
            except anthropic.APIStatusError as e:
                if e.status_code in (403, 429, 529):
                    wait = (attempt + 1) * 10
                    time.sleep(wait)
                else:
                    raise
        raise RuntimeError("LLM call failed after 3 retries")
