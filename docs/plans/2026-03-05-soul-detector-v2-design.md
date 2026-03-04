# Soul Detector V2.0-2.9 — 10-Round Improvement Design

## Context

Super-brain's personality detector hit a plateau at MAE 0.184 (V1.8) after 22 iterations of prompt engineering. The core problem: 20-turn casual conversation doesn't generate enough signal to reliably detect 66 personality traits. Prompt optimization has diminishing returns.

This design applies SoulMap's methodology — Deep Listening, Incisive Questions, Think Slow, Gap Analysis, and the four-layer Soul model — to break through the plateau by fundamentally changing HOW we collect personality signal, then expanding WHAT we detect.

## SoulMap Method Summary (from source docs)

Three source documents inform this design:

1. **SoulMap Method** (46 slides): Three-stage conversation (Deep Listening → Dialog → Interaction), 10 Component listening (Nancy Kline), DAIM Push/Pull dynamics, Gap Analysis, Host Intention Graph
2. **SoulMap Interpretation** (61 slides): AGI = Human Intention × LLM Attention, RL-driven conversation (Alpha Talk), conversation-based RL for prompt optimization, micro evaluation metrics
3. **RL + LLM for L5** (72 slides): Intention Graph construction (Professional Base → Best Practice → Routing → Personalized → Intention), Random Walk, Chain of Interaction

## Soul Four-Layer Model

```
┌─────────────────────────────────┐
│ Layer 4: Intention Graph        │  goals, desires, constraints
├─────────────────────────────────┤
│ Layer 3: Story & History        │  backstory, experiences, turning points
├─────────────────────────────────┤
│ Layer 2: Facts & Features       │  job, relationships, hobbies, education
├─────────────────────────────────┤
│ Layer 1: Character (current)    │  66 personality traits across 13 dimensions
└─────────────────────────────────┘
```

Each layer provides context that improves detection of the layers below it. Facts inform Character detection; Story validates Character; Intentions cross-check Character consistency.

## 10-Round Improvement Plan

### Phase 1: Character Detection Breakthrough (V2.0 — V2.2)

#### V2.0 — Deep Listening Conversation Strategy

**Problem**: Current 3-phase casual Chatter (light → opinions → deeper) is too shallow. Hard-to-detect traits (humor_self_enhancing, social_dominance, mirroring_ability, information_control, competence) never get enough signal.

**Solution**: Replace casual Chatter with Deep Listening based on SoulMap's 10 Component method.

Current Chatter system prompt:
```
"You are having a natural conversation with someone you've been chatting with.
Be a normal, genuine person. Ask follow-up questions naturally."
```

V2.0 Chatter system prompt principles:
```
10 Components (Nancy Kline's Thinking Environment):
1. Attention — Full presence, never interrupt mid-thought
2. Ease — No rush, no agenda, no pushing
3. Equality — Treat user as equal thinking partner
4. Appreciation — Honor user's openness ("that's interesting")
5. Encouragement — Gently invite deeper exploration only when ready
6. Feelings — All emotions welcome, never judge
7. Information — Share relevant info when it helps user think
8. Diversity — Respect different perspectives
9. Incisive Questions — Remove limiting assumptions (introduced in later turns)
10. Place — Create psychological safety
```

Implementation changes:
- `_build_chatter_system()`: Rewrite to use 10 Component principles
- Chatter produces shorter responses (1-2 sentences) to maximize user output
- Phase split: Turn 1-14 pure Deep Listening, Turn 15-20 introduce Incisive Questions
- Speaker responds with longer messages (feels heard → talks more)

Expected: MAE improvement from more raw signal. Target < 0.17.

#### V2.1 — Think Slow: Periodic Soul Extraction

**Problem**: Current Detector reads all 20 turns at once. Information overload + recency bias.

**Solution**: Introduce periodic "Think Slow" extraction every 5 turns.

```
Turn 1-5:   conversation → ThinkSlow_1 → initial Character sketch + confidence map
Turn 6-10:  conversation → ThinkSlow_2 → update Character, flag uncertain traits
Turn 11-15: conversation → ThinkSlow_3 → update, focus on uncertain traits
Turn 16-20: conversation → ThinkSlow_4 → final Character profile
```

New module: `think_slow.py`
```python
class ThinkSlowResult(BaseModel):
    partial_profile: PersonalityDNA      # current best estimate
    confidence_map: dict[str, float]     # per-trait confidence (0-1)
    low_confidence_traits: list[str]     # traits needing more signal
    observations: list[str]             # key behavioral observations so far
```

Each ThinkSlow receives:
- Full conversation history (all turns so far)
- Previous ThinkSlow result (for anchoring, not blind redetection)
- Focus list: traits flagged as low-confidence in previous round

Implementation: Smaller LLM call per ThinkSlow (only 10-15 traits per call, focused on uncertain ones + a random sample for drift detection).

Expected: Better trait stability, confidence data for V2.2. Target MAE < 0.16.

#### V2.2 — Gap-Aware Chatter with Incisive Questions

**Problem**: Chatter doesn't know which traits still lack evidence. Wasted turns on already-detected traits.

**Solution**: Chatter reads ThinkSlow confidence map and steers conversation toward low-confidence traits using Incisive Questions.

New component: `trait_topic_map.py`
```python
# Maps each trait to natural conversation topics that would reveal it
TRAIT_TOPIC_MAP = {
    "social_dominance": [
        "How do you handle disagreements at work?",
        "When you're in a group project, what role do you usually take?",
        "Tell me about a time you had to stand up for something."
    ],
    "humor_self_enhancing": [
        "What do you do when things go wrong — do you find humor in it?",
        "Do you have a funny story about a bad day?",
    ],
    "information_control": [
        "Are you the kind of person who shares everything or keeps cards close?",
        "How much do you share about yourself when meeting new people?",
    ],
    # ... 66 traits, each with 3-5 natural topics
}
```

Chatter integration:
```python
# After ThinkSlow_2 (turn 10):
low_conf = think_slow_result.low_confidence_traits[:5]  # top 5 uncertain
suggested_topics = [TRAIT_TOPIC_MAP[t][0] for t in low_conf]
# Inject into Chatter system prompt as "suggested conversation directions"
# NOT as direct personality probes — natural conversational steering
```

This is the core **Incisive Questions** mechanism from SoulMap Method. The questions remove the "assumption" that we can detect a trait from passive observation — instead we create the conditions for the trait to manifest.

Expected: Significant drop in stubbornly-hard traits. Target MAE < 0.15.

---

### Phase 2: Soul Expansion (V2.3 — V2.5)

#### V2.3 — Facts & Features Detection

Extend `models.py` with Soul layers:

```python
class Fact(BaseModel):
    """A factual observation about the user."""
    category: str       # "job", "relationship", "hobby", "education", "location", "family"
    content: str        # "software engineer at a startup"
    confidence: float   # 0-1
    source_turn: int    # which turn revealed this

class SoulProfile(BaseModel):
    """Complete Soul: Character + Facts + Story + Intentions."""
    id: str
    version: str = "2.0"
    personality: PersonalityDNA          # existing 66 traits
    facts: list[Fact] = []              # V2.3
    story: list[StoryEvent] = []        # V2.4
    intentions: IntentionGraph = None   # V2.6
    gaps: SoulGap = None                # V2.8
```

Facts extraction happens inside ThinkSlow — nearly free since the LLM is already reading the conversation. Add a "facts" section to the ThinkSlow prompt.

Categories to detect:
- Job/career (role, industry, seniority, satisfaction)
- Relationships (partner, children, close friends, conflicts)
- Hobbies/interests (what they do for fun, passions)
- Education (level, field, attitude toward learning)
- Location/lifestyle (urban/rural, routine, living situation)
- Family background (siblings, parents, upbringing indicators)

Eval metric: Facts Precision & Recall against ground-truth profile. Target F1 > 0.7.

#### V2.4 — Story Extraction

```python
class StoryEvent(BaseModel):
    """A significant life event or experience."""
    description: str           # "went through a difficult breakup last year"
    emotional_tone: str        # "painful", "growth", "neutral", "joyful"
    themes: list[str]          # ["loss", "resilience", "trust"]
    personality_signals: dict  # {"trust": "likely lowered", "anxiety": "may be elevated"}
    source_turns: list[int]    # which turns contain this story
```

Story extraction also happens in ThinkSlow. The Deep Listening approach naturally elicits stories — people tell stories when they feel heard.

Key: extract not just the event but its **personality signal**. "Went through betrayal" → trust↓, anxiety↑. "Overcame adversity alone" → locus_of_control↑, self_reliance↑.

Eval metric: Story Recall (did we catch the stories the ground-truth profile contains?). Target > 0.6.

#### V2.5 — Facts→Character Cross-Correction

Use Facts + Story as Bayesian priors for Character detection.

```
Example:
  Detected Fact: "10-year military service"
  Detected Story: "combat deployment, describes it as formative"
  → Bayesian update:
    - self_discipline prior shifts UP (military correlation)
    - emotional_volatility detection needs more care (military suppression pattern)
    - compliance may be artificially HIGH (trained obedience ≠ personality)
    - locus_of_control needs context (military = external authority, but combat = self-reliance)
```

Implementation: A post-ThinkSlow correction step that reads Facts + Story + current trait estimates and applies soft adjustments. NOT hard rules (lesson from V1.0 regression). Soft Bayesian updates: ±0.05-0.10 per relevant Fact/Story.

Expected: MAE < 0.13 through context-informed detection.

---

### Phase 3: Intention Graph (V2.6 — V2.7)

#### V2.6 — Intention Graph Detection

Reuse `communication-dna/intention_graph/` pipeline (Clarify → Expand → Connect), adapted for personal life intentions:

Domain adaptation:
- Communication-dna IG: "user wants to build a product" → PRD
- Soul IG: "user wants career change" / "user wants to fix relationship" / "user wants personal growth"

Intention categories:
- Career goals (promotion, pivot, entrepreneurship, retirement)
- Relationship goals (find partner, fix marriage, family planning)
- Personal growth (learn skill, overcome fear, health improvement)
- Lifestyle (move, financial goals, travel, creativity)
- Emotional (peace, confidence, connection, meaning)

Detection happens in Dialog phase (turns 15-20) through Pull questions about goals and desires. ThinkSlow extracts intention nodes and relationships.

```python
class IntentionNode(BaseModel):
    description: str            # "wants to start own business"
    category: str               # "career"
    strength: float             # 0-1 how strongly expressed
    constraints: list[str]      # ["financial risk", "family obligations"]
    related_traits: list[str]   # ["locus_of_control", "actions", "social_dominance"]

class IntentionGraph(BaseModel):
    nodes: list[IntentionNode]
    edges: list[IntentionEdge]  # relationships between intentions
    end_goal: str               # primary life goal if discernible
```

Eval: Node F1 and Edge F1 against ground-truth intention graphs. Target Node F1 > 0.7.

#### V2.7 — Intention↔Character Cross-Validation

Core insight: Intentions and Character should be consistent. Contradictions reveal detection errors.

```
Intention: "wants to lead a team, start a company"
Character: social_dominance = 0.3, locus_of_control = 0.4
→ CONTRADICTION: strong leadership intention but low dominance/control traits
→ Resolution: either intention is aspirational (not personality-driven)
   OR trait detection was wrong (suppressed in casual chat, revealed in goals)
→ Action: flag for additional Incisive Questions targeting these traits
```

Implementation:
1. Define expected trait ranges for each intention category
2. After IG detection, compare against Character profile
3. Log contradictions as "cross-validation alerts"
4. In live conversation: use contradictions to generate targeted Incisive Questions
5. In eval: measure contradiction rate as quality signal

Expected: MAE < 0.12 through contradiction-driven refinement.

---

### Phase 4: Soul Completeness (V2.8 — V2.9)

#### V2.8 — Soul Gap Analysis

```python
class SoulGap(BaseModel):
    """What we don't know about this user's Soul."""
    missing_facts: list[str]            # facts categories not yet observed
    low_confidence_traits: list[str]    # traits with confidence < 0.5
    unexplored_intentions: list[str]    # intention categories not discussed
    contradictions: list[str]           # cross-validation conflicts
    suggested_questions: list[str]      # Incisive Questions to fill gaps
    completeness_score: float           # 0-1, overall Soul coverage

    @property
    def layer_scores(self) -> dict:
        return {
            "character": ...,    # % of traits with confidence > 0.6
            "facts": ...,        # % of fact categories observed
            "story": ...,        # number of story events detected
            "intentions": ...,   # % of intention categories explored
        }
```

Gap Analysis runs after each ThinkSlow cycle. It drives the Chatter's next moves:
- High gaps in Facts → steer toward factual topics
- High gaps in Character → use trait-specific Incisive Questions
- High gaps in Intentions → shift to Dialog phase (Pull questions about goals)

Eval metric: Soul Completeness Score. Target > 80% coverage across all four layers.

#### V2.9 — Complete Soul Profile + DAIM Integration

Final integration round:
1. **Unified SoulProfile output**: All four layers in one structured document
2. **DAIM (Dynamic Adaptive Influence Model) initial integration**:
   - Think Slow computes 4 variables: Competence, Commitment, Urgency, Trust
   - These variables determine Listen/Pull/Push ratio for remaining turns
   - Low Trust → more Listen; High Trust + High Gap → more Pull
3. **Comprehensive eval framework**:

| Metric | Target |
|--------|--------|
| Character MAE | < 0.12 |
| Character ≤0.25 rate | > 85% |
| Facts F1 | > 0.75 |
| Story Recall | > 0.70 |
| Intention Node F1 | > 0.75 |
| Soul Completeness | > 80% |
| Cross-validation consistency | > 90% |

---

## Architecture Overview

```
                    ┌──────────────┐
                    │  SoulProfile │
                    │  (output)    │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
         ┌────▼────┐  ┌───▼────┐  ┌───▼─────┐
         │Character│  │ Facts  │  │Intention│
         │Detector │  │ Story  │  │ Graph   │
         └────┬────┘  │Extract │  │Detector │
              │       └───┬────┘  └───┬─────┘
              │           │           │
              └─────┬─────┘           │
                    │                 │
              ┌─────▼─────┐           │
              │Think Slow │◄──────────┘
              │(periodic) │
              └─────┬─────┘
                    │
              ┌─────▼─────┐     ┌──────────┐
              │Gap Analysis│────►│  DAIM    │
              └─────┬─────┘     │(strategy)│
                    │           └────┬─────┘
              ┌─────▼─────┐         │
              │  Chatter  │◄────────┘
              │(Deep Listen│
              │+Incisive Q)│
              └─────┬─────┘
                    │
              ┌─────▼─────┐
              │  Speaker  │
              │(method    │
              │ actor)    │
              └───────────┘
```

## Key Design Principles

1. **Incisive Questions are the breakthrough** — not better prompts, but better conversations
2. **Think Slow enables everything** — periodic extraction provides confidence data, drives gap-aware conversation
3. **Cross-layer validation** — each new layer improves detection of all other layers
4. **Soft corrections only** — learned from V1.0 regression: hard rules confuse LLMs, Bayesian updates work
5. **YAGNI** — each round adds one capability, fully evaluated before moving on
6. **Closed-loop eval** — generate profile → conversation → detect → compare, for every layer

## Eval Strategy

Each round uses the existing eval framework (eval_conversation.py) extended with:
- V2.0: Same eval, new Chatter prompts
- V2.1: Track per-ThinkSlow intermediate MAE
- V2.2: Track trait-level MAE improvement for formerly-stubborn traits
- V2.3: Add Facts ground-truth to generated profiles, measure F1
- V2.4: Add Story ground-truth, measure recall
- V2.5: Track MAE improvement from cross-correction
- V2.6: Add Intention ground-truth, measure Node/Edge F1
- V2.7: Track contradiction rate and resolution
- V2.8: Add Soul Completeness score
- V2.9: Full composite eval across all metrics

Ground-truth profiles expand progressively:
```python
# V2.0: same as current
profile = generate_profile(seed=42)  # 66 traits

# V2.3+: extended profile
profile = generate_soul_profile(seed=42)
# → 66 traits + facts + story + intentions
```

## Dependencies

- `communication-dna/intention_graph/`: Reuse for Round 7-8 (IG detection)
- `communication-dna/catalog.py`: Reference for communication style overlay (future)
- `anthropic` SDK: All LLM calls
- `pydantic`: Data models
