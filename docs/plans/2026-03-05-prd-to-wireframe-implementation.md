# PRD → Wireframe PDCA Pipeline — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a 3-stage pipeline (InterfacePlan → AssetAnalyzer → WireframeGenerator) that converts PRDs into production-quality wireframes, validated against golden samples via PDCA.

**Architecture:** Follows WIREFRAME_GENERATION_GUIDE.md's 3-stage pipeline. Each stage is an independent LLM-powered generator class. Golden samples provide ground-truth wireframes for PDCA evaluation. All JSON schemas match the guide exactly.

**Tech Stack:** Python 3.12, anthropic SDK, pydantic 2.x, pytest. SVG rendering via string templates.

---

### Task 1: Wireframe Data Models

**Files:**
- Create: `intention_graph/wireframe_models.py`
- Test: `tests/test_wireframe_models.py`

**Step 1: Write the failing test**

```python
"""Tests for wireframe data models."""
import pytest
from intention_graph.wireframe_models import (
    InterfaceSpec, InterfacePlan,
    AssetEntry, AssetTable,
    WireframeElement, WireframeInterface, WireframeSpec,
)

def test_interface_spec_creation():
    spec = InterfaceSpec(
        index=1, id="main_menu", name="主菜单", type="page",
        dimensions={"width": 1080, "height": 1920},
        description="主菜单界面",
    )
    assert spec.id == "main_menu"
    assert spec.type == "page"
    assert spec.belongs_to is None
    assert spec.navigation_from == []

def test_interface_plan_creation():
    plan = InterfacePlan(
        game_title="Test", art_style="pixel",
        global_resolution={"width": 1080, "height": 1920},
        total_interfaces=1, entry_interface="main_menu",
        interfaces=[],
    )
    assert plan.total_interfaces == 1

def test_wireframe_element_creation():
    elem = WireframeElement(
        id="btn_start", type="button",
        rect={"x": 340, "y": 900, "width": 400, "height": 80, "z_index": 2},
        style={"background-color": "#FF6B35"},
    )
    assert elem.type == "button"
    assert elem.asset_id is None
    assert elem.event is None

def test_wireframe_spec_creation():
    spec = WireframeSpec(
        project={"title": "Test", "global_resolution": {"width": 1080, "height": 1920}},
        interfaces=[],
    )
    assert spec.project["title"] == "Test"
    assert spec.modules == []

def test_interface_plan_to_dict():
    plan = InterfacePlan(
        game_title="Test", art_style="pixel",
        global_resolution={"width": 1080, "height": 1920},
        total_interfaces=0, entry_interface="main",
        interfaces=[],
    )
    d = plan.model_dump()
    assert d["game_title"] == "Test"

def test_wireframe_spec_to_dict():
    spec = WireframeSpec(
        project={"title": "Test", "global_resolution": {"width": 1080, "height": 1920}},
        interfaces=[],
    )
    d = spec.model_dump()
    assert "interfaces" in d
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_wireframe_models.py -v`
Expected: FAIL — module not found

**Step 3: Write minimal implementation**

```python
"""Wireframe data models — matches WIREFRAME_GENERATION_GUIDE.md JSON schemas."""
from __future__ import annotations
from pydantic import BaseModel, Field

class InterfaceSpec(BaseModel):
    index: int
    id: str
    name: str
    type: str  # "page" | "popup"
    dimensions: dict = Field(default_factory=lambda: {"width": 1080, "height": 1920})
    description: str = ""
    belongs_to: str | None = None
    navigation_from: list[str] = Field(default_factory=list)
    navigation_to: list[str] = Field(default_factory=list)

class InterfacePlan(BaseModel):
    game_title: str
    art_style: str
    global_resolution: dict = Field(default_factory=lambda: {"width": 1080, "height": 1920})
    total_interfaces: int = 0
    entry_interface: str = ""
    interfaces: list[InterfaceSpec] = Field(default_factory=list)

class AssetEntry(BaseModel):
    id: str
    type: str  # "image" | "audio"
    category: str = ""  # "background" | "character" | "ui" | "music" | "sfx"
    usage: str = ""
    description: str = ""
    implementation: str = "image"  # "image" | "css" | "text"
    dimensions: dict | None = None
    default_label: str = ""
    format: str = "png"
    path: str = ""

class AssetTable(BaseModel):
    schema_version: str = "asset-table-1.1"
    meta: dict = Field(default_factory=dict)
    assets: list[AssetEntry] = Field(default_factory=list)

class WireframeElement(BaseModel):
    id: str
    type: str  # "image" | "text" | "button" | "css"
    asset_id: str | None = None
    inner_text: str | None = None
    rect: dict  # {"x", "y", "width", "height", "z_index"}
    style: dict = Field(default_factory=dict)
    event: str | None = None  # "click" | None
    target_interface_id: str | None = None
    element_class: str = "editable"

class WireframeInterface(BaseModel):
    interface_id: str
    interface_name: str
    module_id: str = ""
    type: str = "page"  # "page" | "popup"
    parents: list[str] = Field(default_factory=list)
    children: list[str] = Field(default_factory=list)
    dimensions: dict = Field(default_factory=lambda: {"width": 1080, "height": 1920})
    elements: list[WireframeElement] = Field(default_factory=list)
    bg_music_asset_id: str | None = None

class WireframeSpec(BaseModel):
    project: dict
    asset_library: dict = Field(default_factory=dict)
    modules: list[dict] = Field(default_factory=list)
    module_connections: list[dict] = Field(default_factory=list)
    interfaces: list[WireframeInterface] = Field(default_factory=list)
```

**Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest tests/test_wireframe_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add intention_graph/wireframe_models.py tests/test_wireframe_models.py
git commit -m "feat: wireframe data models (InterfacePlan, AssetTable, WireframeSpec)"
```

---

### Task 2: Golden Samples — Flappy Bird

**Files:**
- Create: `intention_graph/golden_samples/flappy_bird/interface_plan.json`
- Create: `intention_graph/golden_samples/flappy_bird/wireframe.json`
- Create: `intention_graph/golden_samples/flappy_bird/source.md`
- Create: `intention_graph/golden_samples/README.md`

Collect from internet: Flappy Bird UI analysis, screenshots, design breakdowns.
Structure into interface_plan.json and wireframe.json following the guide's format.

**Step 1: Research Flappy Bird UI** — Use web search to find screenshots and UI analysis.

**Step 2: Create interface_plan.json** — Flappy Bird has ~4 screens:
- start_screen (tap to start)
- gameplay (bird + pipes + score HUD)
- game_over (score + best + medal + restart)
- leaderboard (optional)

**Step 3: Create wireframe.json** — Precise element positions based on real game screenshots.

**Step 4: Validate** — Run model validation on the JSON files.

**Step 5: Commit**

---

### Task 3: InterfacePlanGenerator (Stage 1)

**Files:**
- Create: `intention_graph/interface_plan_generator.py`
- Test: `tests/test_interface_plan_generator.py`

TDD: Write tests first, then implement the generator.

The generator takes a PRD document and produces an interface_plan.json.
LLM call with system prompt that extracts screens, classifies page/popup,
determines navigation relationships.

**Step 1: Write failing tests** (mock LLM, verify output structure)
**Step 2: Implement InterfacePlanGenerator class**
**Step 3: Run tests, verify pass**
**Step 4: Integration test with real API**
**Step 5: Commit**

---

### Task 4: AssetAnalyzer (Stage 2.1)

**Files:**
- Create: `intention_graph/asset_analyzer.py`
- Test: `tests/test_asset_analyzer.py`

Takes PRD + InterfacePlan → AssetTable.
LLM call that derives needed assets (backgrounds, UI elements, audio).

**Step 1-5: Same TDD pattern as Task 3**

---

### Task 5: WireframeGenerator (Stage 3)

**Files:**
- Create: `intention_graph/wireframe_generator.py`
- Test: `tests/test_wireframe_generator.py`

Takes PRD + InterfacePlan + AssetTable → WireframeSpec.
LLM call that produces pixel-precise layouts.
Optional `reference_wireframe` parameter for PDCA mode.

**Step 1-5: Same TDD pattern**

---

### Task 6: WireframeQuality Evaluator (PDCA Check)

**Files:**
- Create: `intention_graph/wireframe_quality.py`
- Test: `tests/test_wireframe_quality.py`

Structural metrics: screen_coverage, element_coverage, navigation_f1, layout_similarity.
LLM-as-judge: faithfulness, ux_quality, completeness.

**Step 1-5: Same TDD pattern as prd_quality.py**

---

### Task 7: End-to-End Pipeline + PDCA Iteration

**Files:**
- Modify: `intention_graph/__init__.py` (add exports)
- Create: `demo_wireframe.py` (CLI demo)

Full pipeline: PRD → InterfacePlan → AssetTable → Wireframe → Evaluate vs Golden.
Run PDCA iterations to improve quality.

**Step 1: Wire up full pipeline**
**Step 2: Run against Flappy Bird golden sample**
**Step 3: Evaluate and iterate prompts**
**Step 4: Commit**

---

### Task 8: Additional Golden Samples + Broader Testing

Add PvZ, Hollow Knight golden samples.
Run PDCA across all samples, aggregate quality metrics.
Iterate prompts until all samples pass quality thresholds.
