# Intention Graph Detector Design

## Overview

Build an Intention Detector that extracts structured intention graphs from dialogue, analogous to how communication-dna extracts communication style feature vectors. The detector reconstructs a user's hidden Intention Graph — a probabilistic action-space graph where nodes are concrete behavioral intentions, edges are transition probabilities, and the overall distribution is shaped by the individual's personality (DNA).

## Core Concepts

### What is an Intention Graph?

An Intention Graph is a probabilistic directed graph representing a person's action space:

- **Nodes** are concrete behavioral intentions (executable actions with clear goals)
- **Edges** are transition probabilities — the likelihood of "walking" from one action to the next
- **Probability distribution** is shaped by the individual's personality (CommunicationDNA)
- **End Goal** biases the random walk toward a target destination
- **Node states** are either completed or pending; completed nodes are skipped
- **The graph evolves** as the relationship progresses — new goals emerge, end goals shift

### Two Graph Perspectives

| Dimension | Host Graph | User Graph |
|-----------|-----------|------------|
| Visibility | Known, actively managed by the system | Unknown, must be reconstructed |
| Construction | System/domain expert presets + dynamic adjustment | Extracted from user dialogue (**this is what the Detector does**) |
| DNA source | Host's configured personality | Detected via communication-dna |
| End Goal | System-defined | Inferred (may be wrong, needs Clarify) |
| Evolution | Updates based on completion state + relationship progress | Incrementally reconstructed after each conversation |

### Cross-Domain Universality

The graph structure and walk mechanism are domain-agnostic. Only the action space differs:

| Domain | Action Examples | End Goal Example |
|--------|----------------|-----------------|
| Therapy | "identify triggers" -> "practice mindfulness" | "healthy emotional regulation" |
| PRD | "define core features" -> "design API" | "ship MVP" |
| Relationship | "get phone number" -> "first date" -> "propose" | "marriage" |
| Shopping | "set budget" -> "compare products" -> "purchase" | "buy the right laptop" |

Domain-agnostic core: probability transitions + DNA adjustment + End Goal pull + state marking + graph evolution.

Domain-specific parts: action node libraries, typical path templates, domain-specific relation types.

## Data Model

### ActionNode

```python
class ActionNode(BaseModel):
    id: str                                # "int_001"
    text: str                              # "order steak delivery"
    domain: str                            # "relationship" / "therapy" / "prd" / "shopping"
    source: Literal["expressed", "inferred"]
    status: Literal["pending", "completed"]
    confidence: float                      # 0.0-1.0
    specificity: float                     # 0.0(abstract) -> 1.0(concrete)
    evidence: list[Evidence]
    completed_at: datetime | None = None
```

### Transition

```python
class Transition(BaseModel):
    from_id: str
    to_id: str
    base_probability: float                # base transition probability
    dna_adjusted_probability: float        # after DNA personality adjustment
    relation: Literal[
        "next_step",                       # sequential next action
        "decomposes_to",                   # parent -> child decomposition
        "alternative",                     # mutually exclusive paths
        "enables",                         # precondition
        "evolves_to",                      # goal evolution (marriage -> golden anniversary)
    ]
    confidence: float
```

### IntentionGraph

```python
class IntentionGraph(BaseModel):
    nodes: list[ActionNode]
    transitions: list[Transition]
    end_goal: str | None                   # current end goal node ID
    dna_profile: CommunicationDNA | None   # personality driving probability distribution
    completed_path: list[str]              # completed nodes in temporal order
    evolution_history: list[GraphSnapshot]
    ambiguities: list[Ambiguity]
    summary: str
```

### Ambiguity

```python
class Ambiguity(BaseModel):
    node_id: str                           # which node has the ambiguity
    branches: list[str]                    # possible branch node IDs
    incisive_question: str                 # suggested clarifying question
    information_gain: float                # how much uncertainty this question resolves
```

### GraphSnapshot

```python
class GraphSnapshot(BaseModel):
    timestamp: datetime
    trigger: str                           # what triggered the change
    added_nodes: list[str]
    removed_nodes: list[str]
    new_end_goal: str | None
```

## Architecture: Three-Stage Pipeline

### Stage 1: Connect — Extract Nodes + Infer Transitions

**Goal**: Reconstruct the initial skeleton of the User Graph from dialogue.

```
Dialogue text + speaker_id
    |
[Step 1a] Extract ActionNodes (expressed behavioral intentions)
    |
[Step 1b] Infer Transitions (relationships + base probabilities)
    |
[Step 1c] Identify Key Intention (core intent / possible End Goal)
    |
Output: Initial IntentionGraph (expressed nodes only)
```

**Step 1a — Node Extraction**: Scan dialogue for all concrete behavioral intentions expressed by the target speaker. Use chain-of-thought: quote evidence first, then conclude the intention. Assess confidence from language certainty cues ("must/definitely" = high, "maybe/perhaps" = low) and mark completed items.

**Step 1b — Relation Inference**: Given all extracted nodes + original dialogue, infer pairwise relationships and transition probabilities. Batch if nodes > 15 (similar to DNA's 5-batch strategy).

**Step 1c — Key Intention / End Goal**: Attempt to identify the End Goal. Mark with lower confidence since ultimate goals are often implicit.

### Stage 2: Expand — Fill Hidden Nodes + DNA Probability Adjustment

**Goal**: Complete the graph with actions the user didn't mention but must logically exist, and adjust probabilities using personality.

```
Initial IntentionGraph + CommunicationDNA (optional)
    |
[Step 2a] Sub-step decomposition: expand abstract nodes into child actions
    |
[Step 2b] Path completion: infer missing intermediate steps
    |
[Step 2c] DNA probability adjustment: modify transition probabilities using personality traits
    |
Output: Expanded IntentionGraph (with inferred nodes)
```

**Step 2a — Decomposition**: Triggered when node specificity < 0.5. Decompose until leaf nodes reach specificity >= 0.7. Similar to HTN (Hierarchical Task Network) decomposition.

**Step 2b — Path Completion**: When user expressed A and C but B must exist between them, infer B. Example: "want to change jobs" -> ??? -> "got an offer" becomes "want to change jobs" -> "update resume" -> "apply" -> "interview" -> "got an offer".

**Step 2c — DNA Adjustment**: If a CommunicationDNA profile is available, adjust transition probabilities based on personality traits:
- High directness -> higher probability of skipping intermediate steps
- High hedging_frequency -> higher probability of safe/conservative paths
- High vulnerability_willingness -> higher probability of deep disclosure paths

This is the key integration point with communication-dna.

### Stage 3: Clarify — Prune Ambiguity + Generate Incisive Questions

**Goal**: When the possibility space is too large, find the highest-information-gain questions to prune it.

```
Expanded IntentionGraph
    |
[Step 3a] Ambiguity detection: find high-uncertainty branch points
    |
[Step 3b] Question generation: generate Incisive Question for each ambiguity
    |
[Step 3c] Question ranking: sort by information gain, select top-K
    |
Output: Final IntentionGraph + ranked Incisive Questions
```

**Ambiguity condition**: A node has >= 2 outgoing transitions with probability difference < 0.3.

**Incisive Question criteria**:
1. One question eliminates >= 50% of possible paths
2. Easy for user to answer (no deep thought required)
3. Natural and non-intrusive (doesn't reveal system's reasoning)

**Information gain**: Based on Shannon entropy — calculate current entropy of transition distribution, simulate each possible answer's effect on the distribution, rank by expected entropy reduction.

## Evaluation Strategy

### Closed-Loop Testing

```
Known IntentionGraph (ground truth)
    |
[Graph Speaker] Generate simulated dialogue from known graph
    |
[Intention Detector] Extract IntentionGraph from dialogue
    |
[Graph Comparator] Compare extracted vs ground truth
    |
Output: Evaluation metrics
```

### Test Cases: Multi-Domain Synthetic Graphs

| Case | Domain | Nodes | Complexity | Characteristics |
|------|--------|-------|-----------|-----------------|
| 1 | Relationship | ~8 | Medium | Linear path + 1 branch |
| 2 | PRD | ~12 | High | Multi-layer decomposition + parallel subtasks |
| 3 | Therapy | ~6 | Medium | Many implicit intentions, low specificity |
| 4 | Shopping | ~10 | Medium | Many conflicting paths (A vs B) |
| 5 | Career | ~15 | High | Long chain + End Goal evolution |
| 6 | Simple task | ~4 | Low | Baseline: food delivery level simplicity |

### Metrics

**Node-level**:
- Node recall: ground truth nodes matched / total ground truth nodes
- Node precision: correct extracted nodes / total extracted nodes
- Key Intention accuracy: core intent correctly identified

**Edge/Relation-level**:
- Edge F1: relation type correctness
- Probability MAE: mean absolute error of transition probability estimates

**Graph-level**:
- Graph Edit Distance (GED): operations needed to transform extracted -> ground truth
- End Goal accuracy: correct end goal identification rate

### Optimization Targets

| Version | Target |
|---------|--------|
| v0.1 | Node recall >= 70%, Key Intention accuracy >= 60% |
| v0.5 | Node F1 >= 80%, Edge F1 >= 60%, End Goal >= 70% |
| v1.0 | Node F1 >= 90%, Edge F1 >= 75%, Probability MAE <= 0.15 |

## Project Structure

```
communication-dna/
├── communication_dna/          # Existing: communication style detection
│   ├── models.py
│   ├── catalog.py
│   ├── detector.py
│   ├── speaker.py
│   └── ...
│
├── intention_graph/            # New: intention graph extraction
│   ├── models.py               # ActionNode, Transition, IntentionGraph
│   ├── detector.py             # Three-stage pipeline entry point
│   ├── connect.py              # Stage 1: extract + associate
│   ├── expand.py               # Stage 2: decompose + complete + DNA adjust
│   ├── clarify.py              # Stage 3: ambiguity detection + question generation
│   ├── graph_speaker.py        # Evaluation: generate dialogue from known graph
│   └── comparator.py           # Evaluation: graph comparison + metrics
│
├── eval_intention.py           # Evaluation script (like eval_detector.py)
│
├── tests/
│   ├── test_intention_models.py
│   ├── test_connect.py
│   ├── test_expand.py
│   ├── test_clarify.py
│   └── test_intention_closed_loop.py
│
└── examples/
    └── analyze_intentions.py   # Full workflow example
```

### Dependencies

intention_graph.expand imports communication_dna.detector (to get DNA profile) and communication_dna.models (CommunicationDNA type). The integration is optional — Expand works with base probabilities if no DNA profile is provided, and uses DNA-adjusted probabilities when available. The two modules remain loosely coupled.

## Key Research References

- **DiscoverLLM (2026)**: Intent co-construction — users discover intents through exploration, not pre-existing
- **IntentDial (2023)**: Dynamic extensible intent graph with RL-based traversal
- **IGC-RC (2024)**: Intention Knowledge Graph with 6 edge types, 351M edges from session data
- **Nous (2025)**: Shannon entropy-based information gain for Socratic intent clarification
- **Plan Recognition as Planning (Ramirez & Geffner, 2009)**: Goal recognition reduced to planning
- **AutoToM (2025)**: LLM + Bayesian inverse planning hybrid for Theory of Mind
- **RIFTS (Microsoft, ACL 2025)**: LLMs are 3x less likely to clarify than humans — Clarify stage addresses this
- **HTN Planning (Holler 2018)**: Hierarchical task decomposition for goal recognition
- **Baker/Tenenbaum (2009)**: Bayesian inverse planning — treat humans as approximate rational planners
