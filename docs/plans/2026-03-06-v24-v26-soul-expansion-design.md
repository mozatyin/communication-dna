# V2.4-V2.6 Soul Expansion — Design Doc

## Context

V2.3.1 achieves 20t MAE 0.189 with 96% of trait estimates within 0.40 of ground truth. The personality detection layer is mature. Now we expand the Soul model beyond personality to capture facts, reality, intentions, and gaps — the full vision from the Dynamic Soul Architecture.

## Architecture: Three Separate Extractors + Adaptive Frequency

```
                 ┌─────────────────────────┐
                 │       Soul Model         │
                 │ character + facts +      │
                 │ reality + intentions +   │
                 │ gaps + secrets           │
                 └────────┬────────────────┘
                          │ accumulated
          ┌───────────────┼───────────────┐
          │               │               │
   ┌──────▼──────┐ ┌─────▼──────┐ ┌──────▼──────┐
   │ ThinkSlow   │ │FactExtract │ │ ThinkDeep   │
   │ (traits)    │ │(facts+real │ │(intent+gaps │
   │ adaptive    │ │ +secrets)  │ │ +bridge Qs) │
   │ existing    │ │ V2.4 NEW   │ │ V2.5 NEW    │
   └──────┬──────┘ └─────┬──────┘ └──────┬──────┘
          │               │               │
          └───────────────┼───────────────┘
                          │ signals
                 ┌────────▼─────────┐
                 │    Conductor     │ uses Soul context
                 │  (V2.6 enhanced) │ for action selection
                 └────────┬─────────┘
                          │
                 ┌────────▼─────────┐
                 │     Chatter      │
                 └──────────────────┘
```

### Key principle: Separate extractors, separate LLM calls

Each Soul layer gets its own specialized LLM call for maximum precision:
- **ThinkSlow** (existing): personality trait extraction only
- **FactExtractor** (V2.4): facts + reality narrative + secrets
- **ThinkDeep** (V2.5): intentions + reality-intention gaps + bridge questions

### Adaptive frequency per extractor

Each extractor independently adjusts its frequency based on extraction yield:

```python
# High yield (many new results) → increase frequency
# Normal yield → default (every 3 turns)
# Low yield (nothing new) → decrease frequency

def next_interval(current_interval: int, new_items_count: int) -> int:
    if new_items_count >= 3:       # rich extraction
        return max(2, current_interval - 1)
    elif new_items_count == 0:     # nothing new
        return min(5, current_interval + 1)
    else:                          # normal
        return current_interval    # stay at current
```

ThinkDeep remains trigger-based (not periodic) but trigger threshold lowers when FactExtractor finds many intentions or contradictions.

---

## Data Models

### V2.4: Fact + Reality + Secrets

```python
class Fact(BaseModel):
    category: str       # "career", "relationship", "hobby", "education",
                        # "location", "family", "preference", "experience"
    content: str        # "software engineer at a startup"
    confidence: float   # 0.0-1.0
    source_turn: int    # which turn this was extracted from

class Reality(BaseModel):
    summary: str                    # narrative: "Currently a mid-career engineer..."
    domains: dict[str, str]         # {"career": "...", "relationships": "..."}
    constraints: list[str]          # things limiting them
    resources: list[str]            # things they have going for them

class FactExtractionResult(BaseModel):
    new_facts: list[Fact]           # facts found in this cycle
    reality: Reality | None         # updated reality snapshot
    secrets: list[str]              # "avoids discussing family"
                                    # "enthusiasm spikes when discussing travel"
    contradictions: list[str]       # "said values independence but hates decisions"
```

### V2.5: Intention + Gap + Bridge Questions

```python
class Intention(BaseModel):
    description: str                # "wants to start own business"
    domain: str                     # "career", "relationship", "personal_growth",
                                    # "health", "creative", "financial"
    strength: float                 # 0.0-1.0
    blockers: list[str]             # what's in the way

class Gap(BaseModel):
    intention: str                  # what they want
    reality: str                    # where they are
    bridge_question: str            # question exploring this gap
    priority: float                 # 0.0-1.0

class ThinkDeepResult(BaseModel):
    soul_narrative: str             # "This person is at a crossroads..."
    intentions: list[Intention]     # detected intentions
    gaps: list[Gap]                 # reality → intention gaps
    critical_question: str          # THE single most important question
    conversation_strategy: str      # "Shift from listening to exploring risk"
```

### V2.6: Full Soul Model

```python
class Soul(BaseModel):
    id: str

    # Layer 1: Character (existing 66 traits)
    character: PersonalityDNA

    # Layer 2: Facts (accumulated from FactExtractor)
    facts: list[Fact] = []

    # Layer 3: Reality (latest snapshot from FactExtractor)
    reality: Reality | None = None

    # Layer 4: Intentions (from ThinkDeep)
    intentions: list[Intention] = []

    # Cross-layer analysis
    gaps: list[Gap] = []            # reality → intention bridges
    secrets: list[str] = []         # accumulated insights
    contradictions: list[str] = []  # unresolved contradictions
```

---

## Version Breakdown

### V2.4: FactExtractor + Adaptive Frequency

**New module**: `super_brain/fact_extractor.py`
- Separate LLM call (can use smaller model like Haiku for cost)
- Extracts: facts (categorized), reality narrative, secrets, contradictions
- Runs alongside ThinkSlow every N turns (adaptive)
- Deduplicates facts across cycles (same fact not stored twice)

**Adaptive frequency**: Both ThinkSlow and FactExtractor independently adjust their interval (2-5 turns) based on extraction yield from their last cycle.

**Soul model**: Introduce `Soul` class aggregating character + facts + reality + secrets.

**Conductor**: Passes accumulated facts/reality to Chatter context for more informed conversation.

**Eval**: MAE + Soul Coverage (facts_count, reality_populated, secrets_count).

### V2.5: ThinkDeep + Intentions + Gaps

**New module**: `super_brain/think_deep.py`
- Triggered by Conductor (not periodic)
- Receives full Soul state as context
- Produces: intentions, gaps, bridge questions, critical question, strategy
- Uses larger model for strategic analysis

**Trigger conditions**:
- FactExtractor finds 5+ facts AND 0 intentions detected yet
- FactExtractor finds a contradiction
- ThinkSlow info_staleness > 0.8 for 2+ consecutive cycles
- After turn 10 if no intentions detected

**Conductor enhanced**: ThinkDeep.critical_question → "push" mode.

**IncisiveQuestion sources expanded**: trait_gap + reality_gap + intention_gap + contradiction + secret (5 sources instead of 1).

**Eval**: + intention_count, gap_count.

### V2.6: Full Soul Integration

**Conductor uses full Soul context**: Decisions weighted by Soul layer staleness, not just info_entropy.

**IncisiveQuestions from all sources**: Conductor picks from trait gaps, reality gaps, intention gaps, contradictions, and secrets — prioritized by overall Soul coverage needs.

**Adaptive ThinkSlow frequency** fully operational.

**Soul passed to Chatter**: Chatter knows accumulated facts/reality/intentions, can reference them naturally ("You mentioned wanting to start a business earlier...").

**Eval**: Full Soul coverage score (weighted composite of all layers).

---

## Eval Strategy

### Metrics

| Metric | V2.4 | V2.5 | V2.6 |
|--------|------|------|------|
| Character MAE (20t) | ✅ | ✅ | ✅ |
| Character MAE (10t) | ✅ | ✅ | ✅ |
| facts_count | ✅ | ✅ | ✅ |
| reality_populated | ✅ | ✅ | ✅ |
| secrets_count | ✅ | ✅ | ✅ |
| intentions_count | | ✅ | ✅ |
| gaps_count | | ✅ | ✅ |
| soul_coverage_score | | | ✅ |

### Soul Coverage Score (V2.6)

```python
def compute_soul_coverage(soul: Soul) -> float:
    scores = []
    scores.append(min(len(soul.facts) / 10.0, 1.0))         # 10+ facts = full
    scores.append(1.0 if soul.reality else 0.0)               # reality populated
    scores.append(min(len(soul.intentions) / 3.0, 1.0))       # 3+ intentions = full
    scores.append(min(len(soul.gaps) / 2.0, 1.0))             # 2+ gaps = full
    scores.append(min(len(soul.secrets) / 3.0, 1.0))          # 3+ secrets = full
    return sum(scores) / len(scores)
```

### Expected Targets

| Version | Target MAE (20t) | Target Soul Coverage |
|---------|------------------|---------------------|
| V2.3.1 (current) | 0.189 | N/A |
| V2.4 | ≤ 0.185 | facts ≥ 5, reality populated |
| V2.5 | ≤ 0.180 | + intentions ≥ 2, gaps ≥ 1 |
| V2.6 | ≤ 0.175 | coverage_score ≥ 0.70 |

---

## Key Design Principles

1. **Separate extractors for precision**: Each LLM call focuses on one task only
2. **Adaptive frequency from day one**: Extract more when there's more to find
3. **Accumulate, don't discard**: Every cycle adds to the Soul model
4. **Measurable at every step**: Each version has MAE + Soul Coverage
5. **Cost-aware**: FactExtractor can use cheap model (Haiku); ThinkDeep is rare
6. **Backward compatible**: Existing ThinkSlow/ThinkFast/Conductor untouched in V2.4
