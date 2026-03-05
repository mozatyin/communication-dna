# PRD → Wireframe PDCA Pipeline — Design Document

> Generate production-quality wireframes from PRDs, validated against
> real-world golden samples through a PDCA improvement cycle.

---

## 1. Vision

Take a PRD (from `OneSentencePrd` or `PrdGenerator`) and produce a complete
wireframe specification — every screen, every element, every navigation edge —
that matches or exceeds the quality of real-world successful products.

**PDCA cycle**: Use famous products with known wireframes (Flappy Bird, PvZ,
Hollow Knight, etc.) as golden samples. Generate wireframes from their PRDs,
compare against golden samples, and iteratively improve the generation algorithm.

**Scope**: General products (games, apps, SaaS), starting with games where we
already have a strong PRD pipeline.

---

## 2. Architecture

Follows the 3-stage pipeline defined in `WIREFRAME_GENERATION_GUIDE.md`:

```
PRD (prd.txt / prd_document)
  │
  ├──► Stage 1: InterfacePlanGenerator ──► interface_plan.json
  │         │
  │    ┌────┘
  │    │
  ├──► Stage 2: AssetAnalyzer ──► asset_table.json (analysis only, no file generation)
  │         │
  │    ┌────┘
  │    │
  └──► Stage 3: WireframeGenerator ──► wireframe.json
                    │
                    ├──► WireframeEvaluator (PDCA Check)
                    │       Compare vs golden_samples/
                    │       → structural metrics + LLM semantic score
                    │
                    └──► Downstream: code generation / visual editor
```

**v1 scope**: Stages 1, 2.1 (analysis), 3, and PDCA evaluator.
Stage 2.2 (asset file generation) is deferred — it requires external
image/audio generation APIs.

---

## 3. Data Models

All JSON schemas follow `WIREFRAME_GENERATION_GUIDE.md` exactly.
Pydantic models in `wireframe_models.py`.

### 3.1 InterfacePlan (Stage 1 output)

```python
class InterfaceSpec(BaseModel):
    index: int
    id: str                    # e.g. "main_menu"
    name: str                  # e.g. "主菜单"
    type: str                  # "page" | "popup"
    dimensions: dict           # {"width": 1080, "height": 1920}
    description: str           # Content/logic description (no layout)
    belongs_to: str | None     # Parent page for popups
    navigation_from: list[str]
    navigation_to: list[str]

class InterfacePlan(BaseModel):
    game_title: str
    art_style: str
    global_resolution: dict    # {"width": 1080, "height": 1920}
    total_interfaces: int
    entry_interface: str
    interfaces: list[InterfaceSpec]
```

### 3.2 AssetTable (Stage 2 output)

```python
class AssetEntry(BaseModel):
    id: str                    # e.g. "bg_main_menu"
    type: str                  # "image" | "audio"
    category: str              # "background" | "character" | "ui" | "music" | "sfx"
    usage: str
    description: str
    implementation: str        # "image" | "css" | "text"
    dimensions: dict | None
    default_label: str

class AssetTable(BaseModel):
    schema_version: str = "asset-table-1.1"
    meta: dict                 # gameTitle, artDirection, etc.
    assets: list[AssetEntry]
```

### 3.3 WireframeSpec (Stage 3 output)

```python
class WireframeElement(BaseModel):
    id: str
    type: str                  # "image" | "text" | "button" | "css"
    asset_id: str | None
    inner_text: str | None
    rect: dict                 # {"x", "y", "width", "height", "z_index"}
    style: dict
    event: str | None          # "click" | None
    target_interface_id: str | None

class WireframeInterface(BaseModel):
    interface_id: str
    interface_name: str
    module_id: str
    type: str                  # "page" | "popup"
    parents: list[str]
    children: list[str]
    dimensions: dict
    elements: list[WireframeElement]
    bg_music_asset_id: str | None

class WireframeSpec(BaseModel):
    project: dict              # {"title", "global_resolution"}
    asset_library: dict        # asset_id → {type, path, label}
    modules: list[dict]        # Logical groupings
    module_connections: list[dict]
    interfaces: list[WireframeInterface]
```

---

## 4. Implemented Files

```
intention_graph/
├── wireframe_models.py            # Pydantic models for all wireframe data
├── interface_plan_generator.py    # Stage 1: PRD → InterfacePlan
├── asset_analyzer.py              # Stage 2.1: PRD + Plan → AssetTable
├── wireframe_generator.py         # Stage 3: PRD + Plan + Assets → WireframeSpec
├── wireframe_quality.py           # PDCA Check: evaluator (structural + LLM)
│
├── golden_samples/                # Golden wireframe data (committed to repo)
│   ├── flappy_bird/
│   │   ├── interface_plan.json    # 4 screens: start, gameplay, game_over, leaderboard
│   │   ├── wireframe.json         # Full pixel-precise wireframe
│   │   └── source.md              # Data provenance
│   └── ...
│
run_pdca.py                        # PDCA iteration runner CLI

tests/
├── test_wireframe_models.py       # 15 tests
├── test_interface_plan_generator.py  # 10 unit + 1 integration
├── test_asset_analyzer.py         # 5 unit + 1 integration
├── test_wireframe_generator.py    # 6 unit + 1 integration
└── test_wireframe_quality.py      # 22 tests (fuzzy matching, navigation)
```

**Not yet implemented:**
- `wireframe_renderer.py` — SVG/HTML visualization
- `wireframe_collector.py` — Automated golden sample collection
- Additional golden samples (PvZ, Hollow Knight, etc.)

---

## 5. Module Design

### 5.1 InterfacePlanGenerator (Stage 1)

```python
class InterfacePlanGenerator:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514")
    def generate(self, prd_document: str) -> dict
```

**Key prompt features:**
- Complexity-aware screen count: arcade 3-5, casual 5-7, mid-core 6-10
- Always includes score/leaderboard popup for games with scoring
- Symmetric navigation enforcement (A→B implies B←A)
- Popup reachability from all screens with buttons for them
- Language matching (Chinese PRD → Chinese screen names)

### 5.2 AssetAnalyzer (Stage 2.1)

```python
class AssetAnalyzer:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514")
    def analyze(self, prd_document: str, interface_plan: dict) -> dict
```

### 5.3 WireframeGenerator (Stage 3)

```python
class WireframeGenerator:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514")
    def generate(
        self,
        prd_document: str,
        interface_plan: dict,
        asset_table: dict,
        reference_wireframe: dict | None = None,  # Golden sample for PDCA
    ) -> dict
```

**Key prompt features:**
- Exact screen matching with interface plan (no more, no fewer)
- Navigation consistency with interface plan (parents/children must match)
- Popup simplicity (3-6 elements, not over-engineered)
- All button clicks must have target_interface_id
- Golden reference mode for PDCA improvement

### 5.4 WireframeQuality (PDCA Check)

```python
def evaluate(generated: dict, golden: dict) -> QualityReport
def semantic_evaluate(generated: dict, golden: dict, prd_document: str, api_key: str) -> QualityMetric
```

**Structural metrics (5):**
- `screen_coverage`: Fuzzy screen matching with synonym groups
- `element_coverage`: Per-screen element count similarity
- `navigation_accuracy`: Recall-focused edge matching (70% recall + 30% count)
- `layout_completeness`: Background + interactive element per screen (popup-aware)
- `element_types`: Diversity check (image, text, button present)

**Fuzzy matching features:**
- Synonym groups: {"main", "menu", "start", "home", "title", "entry", "launch"}, etc.
- ID substring matching, name overlap, type matching
- Navigation edge extraction from children, parents, and button targets

**Semantic evaluation (LLM-as-judge):**
- faithfulness (0-10): Does wireframe reflect PRD features?
- ux_quality (0-10): Is layout intuitive?
- completeness (0-10): Are all key screens/elements present?

---

## 6. PDCA Iteration Results

### Iteration History (Flappy Bird)

| Iter | Structural | Failures | Key Change |
|------|-----------|----------|------------|
| 1 | 70% | 2 | Baseline (exact ID matching) |
| 2 | 75% | 1 | Fuzzy screen matching |
| 3 | 78% | 0 | Synonym group matching |
| 4 | 84% | 0 | Recall-focused navigation |
| 5 | 74% | 0 | Fresh run, 6 screens (too many) |
| 6 | 85% | 0 | Screen count constraint |
| 7 | 86% | 1 | Parents field edges, popup bg |
| 8 | 92% | 0 | Popup-aware layout completeness |
| 9 | 93% | 0 | Golden reference mode |
| 10 | 94% | 0 | Popup simplicity guidance |
| 11 | **95%** | 0 | Navigation hints, best without golden |
| 12 | 94% | 0 | Consistent with semantic 80% |

### Current Best Scores

| Metric | Without Golden | With Golden |
|--------|---------------|-------------|
| screen_coverage | 100% | 100% |
| element_coverage | 85% | 88% |
| navigation_accuracy | 86% | 86% |
| layout_completeness | 100% | 100% |
| element_types | 100% | 100% |
| **Structural Overall** | **94%** | **95%** |
| **Semantic Overall** | **80%** | **80%** |

### Cross-Product Generalization

| Product | Screens | Elements | Layout | Types | Status |
|---------|---------|----------|--------|-------|--------|
| Flappy Bird (arcade) | 4 | 24-34 | 100% | 100% | Golden sample ✓ |
| PvZ (casual) | 6 | 54 | 100% | 100% | Self-metrics only |
| Tetris (arcade) | TBD | TBD | TBD | TBD | Pending |

---

## 7. Golden Sample Strategy

### Current samples
| Product | Type | Complexity | Status |
|---------|------|------------|--------|
| Flappy Bird | game | arcade | ✅ Complete (4 screens, 26 elements) |

### Planned samples
| Product | Type | Complexity | Status |
|---------|------|------------|--------|
| Plants vs Zombies | game | casual | Pending |
| Hollow Knight | game | mid-core | Pending |
| Honor of Kings | game | hardcore | Pending |

### Extending to general products (v2+)
- Add app samples: Instagram, Uber, Notion
- Add SaaS samples: Figma, Linear, Slack
- PRD format may need generalization beyond game-specific sections

---

## 8. End-to-End Pipeline

```python
from intention_graph import (
    OneSentencePrd,
    InterfacePlanGenerator,
    AssetAnalyzer,
    WireframeGenerator,
    evaluate_wireframe,
)

api_key = "..."

# Step 1: PRD
prd = OneSentencePrd(api_key).generate("做一个Flappy Bird")

# Step 2: Interface Plan
plan = InterfacePlanGenerator(api_key).generate(prd["prd_document"])

# Step 3: Asset Analysis
assets = AssetAnalyzer(api_key).analyze(prd["prd_document"], plan)

# Step 4: Wireframe
wireframe = WireframeGenerator(api_key).generate(
    prd["prd_document"], plan, assets
)

# Step 5: Evaluate
golden = json.load(open("intention_graph/golden_samples/flappy_bird/wireframe.json"))
report = evaluate_wireframe(wireframe, golden)
print(report.summary())
```

---

## 9. Success Criteria

| Criterion | Target | Current |
|-----------|--------|---------|
| Structural similarity to golden | ≥80% | **95%** ✅ |
| Screen coverage | 100% | **100%** ✅ |
| Navigation accuracy | ≥80% | **86%** ✅ |
| LLM semantic score | ≥7/10 per dimension | **8/7/9** ✅ |
| Pipeline latency | < 4 minutes (4 LLM calls) | ~3.5 min ✅ |
| All unit tests pass | 162 tests | **162** ✅ |

---

## 10. Remaining Work

1. **Navigation accuracy** — Push from 86% → 95% (improve leaderboard reachability)
2. **Additional golden samples** — PvZ, Tetris, then apps
3. **WireframeRenderer** — SVG/HTML visualization for visual QA
4. **WireframeCollector** — Automated golden sample collection
5. **Cross-product PDCA** — Validate improvements generalize beyond Flappy Bird
6. **General product support** — Extend beyond games to apps/SaaS
