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

**v1 scope**: Stages 1, 3, and PDCA evaluator. Stage 2 (asset analysis) is
included but asset file generation (Stage 2.2 Realize) is deferred — it
requires external image/audio generation APIs.

---

## 3. Data Models

All JSON schemas follow `WIREFRAME_GENERATION_GUIDE.md` exactly.

### 3.1 InterfacePlan (Stage 1 output)

```python
@dataclass
class InterfaceSpec:
    index: int
    id: str                    # e.g. "main_menu"
    name: str                  # e.g. "主菜单"
    type: str                  # "page" | "popup"
    dimensions: dict           # {"width": 1080, "height": 1920}
    description: str           # Content/logic description (no layout)
    belongs_to: str | None     # Parent page for popups
    navigation_from: list[str]
    navigation_to: list[str]

@dataclass
class InterfacePlan:
    game_title: str
    art_style: str
    global_resolution: dict    # {"width": 1080, "height": 1920}
    total_interfaces: int
    entry_interface: str
    interfaces: list[InterfaceSpec]
```

### 3.2 AssetTable (Stage 2 output)

```python
@dataclass
class AssetEntry:
    id: str                    # e.g. "bg_main_menu"
    type: str                  # "image" | "audio"
    category: str              # "background" | "character" | "ui" | "music" | "sfx"
    usage: str
    description: str
    implementation: str        # "image" | "css" | "text"
    dimensions: dict | None
    default_label: str

@dataclass
class AssetTable:
    schema_version: str = "asset-table-1.1"
    meta: dict                 # gameTitle, artDirection, etc.
    assets: list[AssetEntry]
```

### 3.3 WireframeSpec (Stage 3 output)

```python
@dataclass
class WireframeElement:
    id: str
    type: str                  # "image" | "text" | "button" | "css"
    asset_id: str | None
    inner_text: str | None
    rect: dict                 # {"x", "y", "width", "height", "z_index"}
    style: dict
    event: str | None          # "click" | None
    target_interface_id: str | None

@dataclass
class WireframeInterface:
    interface_id: str
    interface_name: str
    module_id: str
    type: str                  # "page" | "popup"
    parents: list[str]
    children: list[str]
    dimensions: dict
    elements: list[WireframeElement]
    bg_music_asset_id: str | None

@dataclass
class WireframeSpec:
    project: dict              # {"title", "global_resolution"}
    asset_library: dict        # asset_id → {type, path, label}
    modules: list[dict]        # Logical groupings
    module_connections: list[dict]
    interfaces: list[WireframeInterface]
```

### 3.4 GoldenSample

```python
@dataclass
class GoldenSample:
    product_name: str
    product_type: str          # "game" | "app" | "saas"
    complexity: str            # "arcade" | "casual" | "mid-core" | "hardcore"
    source: str                # Where the wireframe was sourced from
    interface_plan: InterfacePlan
    wireframe: WireframeSpec
    prd_document: str          # The PRD used (generated or provided)
    notes: str                 # Design rationale
```

---

## 4. New Files

```
intention_graph/
├── wireframe_models.py            # Pydantic models for all wireframe data
├── interface_plan_generator.py    # Stage 1: PRD → InterfacePlan
├── asset_analyzer.py              # Stage 2.1: PRD + Plan → AssetTable
├── wireframe_generator.py         # Stage 3: PRD + Plan + Assets → WireframeSpec
├── wireframe_quality.py           # PDCA Check: evaluator (structural + LLM)
├── wireframe_collector.py         # Collect golden samples from internet
├── wireframe_renderer.py          # WireframeSpec → SVG/HTML visualization
│
├── golden_samples/                # Golden wireframe data (committed to repo)
│   ├── README.md                  # Index of all samples
│   ├── flappy_bird/
│   │   ├── interface_plan.json
│   │   ├── wireframe.json
│   │   └── source.md              # Where data came from
│   ├── plants_vs_zombies/
│   │   ├── interface_plan.json
│   │   ├── wireframe.json
│   │   └── source.md
│   └── ...
│
tests/
├── test_wireframe_models.py
├── test_interface_plan_generator.py
├── test_wireframe_generator.py
├── test_wireframe_quality.py
└── test_wireframe_collector.py
```

---

## 5. Module Design

### 5.1 InterfacePlanGenerator (Stage 1)

```python
class InterfacePlanGenerator:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514")

    def generate(self, prd_document: str) -> dict:
        """PRD text → interface_plan.json dict.

        LLM call with system prompt that:
        1. Extracts all screens from PRD sections 1-4
        2. Classifies each as "page" or "popup"
        3. Determines navigation relationships
        4. Sets appropriate resolution for platform

        For games: gameplay screen, menus, popups, HUD overlays
        For apps: main screens, modals, settings, onboarding
        """
```

**Key design**: The system prompt must understand both game and general product
PRDs. For games, Section 3 (游戏系统) maps to gameplay screens. For apps, feature
descriptions map to functional screens.

### 5.2 AssetAnalyzer (Stage 2.1)

```python
class AssetAnalyzer:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514")

    def analyze(self, prd_document: str, interface_plan: dict) -> dict:
        """PRD + InterfacePlan → asset_table.json dict.

        LLM call that derives:
        - Background images for each screen
        - UI elements (buttons, icons, labels)
        - Character/object sprites (for games)
        - Audio (BGM, SFX)

        Each asset gets: id, type, category, description, implementation type.
        No actual file generation — just the manifest.
        """
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
    ) -> dict:
        """PRD + Plan + Assets → wireframe.json dict.

        LLM call that produces pixel-precise layouts:
        - Element positions (x, y, width, height in absolute pixels)
        - Style properties (colors, fonts, borders)
        - Interaction events (click → navigate to screen)
        - Asset references (which asset_id goes where)

        If reference_wireframe is provided (PDCA mode), the LLM is instructed
        to study the reference and produce a similar-quality layout.
        """
```

**Key design**: The `reference_wireframe` parameter enables the PDCA "Act" phase.
When a golden sample is available for the same product type, it's fed as a
reference to guide the generation toward proven patterns.

### 5.4 WireframeQuality (PDCA Check)

```python
def evaluate(
    generated: dict,           # Generated wireframe.json
    golden: dict,              # Golden sample wireframe.json
) -> QualityReport:
    """Compare generated wireframe against golden sample.

    Structural metrics:
    - screen_coverage: Jaccard similarity of screen IDs
    - element_type_distribution: Per-screen element type histogram similarity
    - navigation_f1: F1 score of navigation edges
    - layout_distance: Normalized position/size distance of matched elements

    Returns QualityReport (same pattern as prd_quality.py).
    """

def semantic_evaluate(
    generated: dict,
    golden: dict,
    prd_document: str,
    api_key: str,
) -> QualityMetric:
    """LLM-as-judge semantic evaluation.

    Scores 3 dimensions (0-10 each):
    - faithfulness: Does wireframe reflect PRD's described features?
    - ux_quality: Is layout intuitive, following UX best practices?
    - completeness: Are all key screens and elements present?
    """
```

### 5.5 WireframeCollector

```python
class WireframeCollector:
    def __init__(self, api_key: str)

    def collect(self, product_name: str, product_type: str = "game") -> GoldenSample:
        """Collect golden wireframe for a known product.

        Pipeline:
        1. Web search for "{product_name} wireframe/UI design/interface design"
        2. Search for screenshots, design breakdowns, UI analyses
        3. LLM synthesizes findings into structured wireframe.json format
        4. Human review recommended before committing as golden sample

        This produces a "best guess" golden sample from public information.
        Manual refinement is expected.
        """
```

### 5.6 WireframeRenderer

```python
class WireframeRenderer:
    @staticmethod
    def to_svg(wireframe: dict, screen_id: str) -> str:
        """Render a single screen as SVG."""

    @staticmethod
    def to_html(wireframe: dict) -> str:
        """Render all screens as interactive HTML with navigation."""
```

---

## 6. PDCA Cycle

### Plan
- System prompts for each stage (InterfacePlan, AssetAnalyzer, WireframeGenerator)
- Complexity-aware rules (arcade: fewer screens, simpler layouts)
- Product-type-aware rules (game vs app vs SaaS)

### Do
```python
prd = OneSentencePrd(api_key).generate("做一个Flappy Bird")
plan = InterfacePlanGenerator(api_key).generate(prd["prd_document"])
assets = AssetAnalyzer(api_key).analyze(prd["prd_document"], plan)
wireframe = WireframeGenerator(api_key).generate(prd["prd_document"], plan, assets)
```

### Check
```python
golden = load_golden_sample("flappy_bird")
report = wireframe_quality.evaluate(wireframe, golden.wireframe)
semantic = wireframe_quality.semantic_evaluate(wireframe, golden.wireframe, prd["prd_document"], api_key)
print(report.summary())
```

### Act
- Analyze failures → adjust system prompts → re-run
- If generated wireframe is better than golden → update golden sample
- Track improvement across iterations

---

## 7. Golden Sample Strategy

### Initial samples (v1)
Start with 4 games matching our PRD complexity tiers:

| Product | Type | Complexity | Why |
|---------|------|------------|-----|
| Flappy Bird | game | arcade | 3 screens, minimal UI, clear reference |
| Plants vs Zombies | game | casual | 5-7 screens, moderate complexity |
| Hollow Knight | game | mid-core | 8-10 screens, menus + gameplay + map |
| Honor of Kings | game | hardcore | 15+ screens, complex menus + social |

### Collection method
1. Web search for UI screenshots, design analyses, game walkthroughs
2. LLM synthesizes into interface_plan.json + wireframe.json
3. Human review and refinement
4. Commit to `golden_samples/` directory

### Extending to general products (v2+)
- Add app samples: Instagram, Uber, Notion
- Add SaaS samples: Figma, Linear, Slack
- PRD format may need generalization beyond game-specific sections

---

## 8. End-to-End Pipeline

```python
# Full pipeline: sentence → PRD → wireframe → evaluate
from intention_graph import OneSentencePrd
from intention_graph.interface_plan_generator import InterfacePlanGenerator
from intention_graph.asset_analyzer import AssetAnalyzer
from intention_graph.wireframe_generator import WireframeGenerator
from intention_graph.wireframe_quality import evaluate, semantic_evaluate

api_key = "..."

# Step 1: PRD (existing)
prd_result = OneSentencePrd(api_key).generate("做一个Flappy Bird")

# Step 2: Interface Plan (new)
plan = InterfacePlanGenerator(api_key).generate(prd_result["prd_document"])

# Step 3: Asset Analysis (new)
assets = AssetAnalyzer(api_key).analyze(prd_result["prd_document"], plan)

# Step 4: Wireframe (new)
wireframe = WireframeGenerator(api_key).generate(
    prd_result["prd_document"], plan, assets
)

# Step 5: Evaluate (new)
golden = load_golden_sample("flappy_bird")
report = evaluate(wireframe, golden["wireframe"])
print(report.summary())
```

---

## 9. Implementation Order

1. **wireframe_models.py** — Pydantic data models
2. **golden_samples/** — Collect first 2 golden samples (Flappy Bird, PvZ)
3. **interface_plan_generator.py** — Stage 1 + tests
4. **asset_analyzer.py** — Stage 2.1 + tests
5. **wireframe_generator.py** — Stage 3 + tests
6. **wireframe_quality.py** — Structural + LLM evaluator + tests
7. **wireframe_renderer.py** — SVG/HTML visualization
8. **PDCA iteration** — Run full pipeline, compare, improve prompts
9. **wireframe_collector.py** — Automate golden sample collection

---

## 10. Success Criteria

- Generated Flappy Bird wireframe achieves ≥80% structural similarity to golden sample
- Generated wireframe has all screens from PRD (100% screen coverage)
- Navigation graph matches golden sample (F1 ≥ 0.9)
- LLM semantic score ≥ 7/10 on all 3 dimensions
- Full pipeline runs in < 2 minutes (3 LLM calls)
