# Soul Detector V2.0-V2.2 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Break through the MAE 0.184 plateau by replacing casual conversation with Deep Listening, adding periodic Think Slow extraction, and gap-aware Incisive Questions.

**Architecture:** Three rounds of changes: V2.0 rewrites the Chatter with 10 Component Deep Listening; V2.1 adds periodic ThinkSlow extraction every 5 turns with confidence tracking; V2.2 feeds ThinkSlow confidence gaps back into the Chatter as Incisive Question targets. Each round is evaluated independently before moving to the next.

**Tech Stack:** Python 3.12, anthropic SDK, pydantic, pytest

---

## V2.0 — Deep Listening Conversation Strategy

### Task 1: Write failing test for new Deep Listening chatter system prompt

**Files:**
- Create: `tests/test_chatter_v2.py`
- Reference: `eval_conversation.py:51-95` (current `_build_chatter_system`)

**Step 1: Write the failing test**

```python
"""Tests for V2.0 Deep Listening Chatter."""

from eval_conversation import _build_chatter_system


def test_deep_listening_prompt_contains_10_components():
    """V2.0 chatter system prompt should reference Deep Listening principles."""
    prompt = _build_chatter_system(turn_number=1, total_turns=20)
    # Must mention key 10 Component principles
    assert "attention" in prompt.lower() or "presence" in prompt.lower()
    assert "ease" in prompt.lower() or "no rush" in prompt.lower()
    assert "appreciation" in prompt.lower()


def test_deep_listening_phase_split():
    """Turns 1-14 = Deep Listening, Turns 15-20 = Incisive Questions."""
    early = _build_chatter_system(turn_number=3, total_turns=20)
    late = _build_chatter_system(turn_number=16, total_turns=20)

    # Early turns should NOT contain incisive question language
    assert "incisive" not in early.lower()
    # Late turns SHOULD contain incisive question language
    assert "incisive" in late.lower() or "targeted" in late.lower()


def test_chatter_prompt_short_response_instruction():
    """Chatter should produce 1-2 sentence responses to maximize speaker output."""
    prompt = _build_chatter_system(turn_number=5, total_turns=20)
    assert "1-2 sentence" in prompt.lower() or "short" in prompt.lower()


def test_chatter_no_personality_probing():
    """Deep Listening should never directly probe personality."""
    for turn in [1, 5, 10, 15, 20]:
        prompt = _build_chatter_system(turn_number=turn, total_turns=20)
        assert "what kind of person" not in prompt.lower()
        assert "describe yourself" not in prompt.lower()
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_chatter_v2.py -v`
Expected: FAIL — current `_build_chatter_system` doesn't have Deep Listening language

**Step 3: Commit test**

```bash
git add tests/test_chatter_v2.py
git commit -m "test: add failing tests for V2.0 Deep Listening chatter"
```

---

### Task 2: Rewrite `_build_chatter_system()` with Deep Listening

**Files:**
- Modify: `eval_conversation.py:51-95`

**Step 1: Implement the Deep Listening chatter system prompt**

Replace the existing `_build_chatter_system` function (lines 51-95) with:

```python
def _build_chatter_system(turn_number: int, total_turns: int) -> str:
    """Build a Chatter system prompt with Deep Listening + Incisive Questions.

    V2.0: Based on Nancy Kline's 10 Component Thinking Environment.
    - Turns 1-14: Pure Deep Listening (create safety, maximize speaker output)
    - Turns 15+: Introduce Incisive Questions (targeted exploration)
    """
    base = (
        "You are a deep listener having a natural conversation. Your goal is to create "
        "a space where the other person feels genuinely heard and opens up naturally.\n\n"
        "DEEP LISTENING PRINCIPLES (follow these throughout):\n"
        "1. Full Attention & Presence — focus entirely on what they're saying, never rush\n"
        "2. Ease — no agenda, no pushing, let the conversation breathe\n"
        "3. Equality — treat them as an equal thinking partner, not a subject\n"
        "4. Appreciation — honor their openness genuinely ('that's interesting', 'I appreciate you sharing that')\n"
        "5. Encouragement — gently invite deeper exploration only when they seem ready\n"
        "6. Feelings — all emotions are welcome, never judge or dismiss\n"
        "7. Information — share relevant bits about yourself when it helps them open up\n"
        "8. Diversity — respect different perspectives without correcting\n"
        "9. Place — create psychological safety through warmth and acceptance\n\n"
        "RESPONSE STYLE:\n"
        "- Keep your messages SHORT (1-2 sentences). Your job is to get THEM talking.\n"
        "- Ask ONE follow-up question per message, not multiple.\n"
        "- Reflect back what you heard before asking the next question.\n"
        "- Share a small personal detail occasionally to build reciprocity.\n\n"
        "IMPORTANT: Do NOT probe their personality, psychology, or ask them to describe "
        "themselves. Never ask 'what kind of person are you' or similar. Never ask "
        "multiple questions in one message.\n\n"
    )

    if turn_number <= 7:
        return base + (
            "CURRENT PHASE: Building rapport. Keep it warm and light — daily life, "
            "interests, recent experiences. Focus on making them feel comfortable. "
            "Let them lead the topics. Mirror their energy level.\n"
            "LISTENER GOAL: Establish trust. Show genuine curiosity about their world."
        )
    elif turn_number <= 14:
        return base + (
            "CURRENT PHASE: Deepening. The conversation is flowing naturally. You can now:\n"
            "- Follow emotional threads ('that sounds like it mattered to you')\n"
            "- Ask about experiences behind opinions ('what happened that made you see it that way?')\n"
            "- Explore how they handle challenges ('how did you deal with that?')\n"
            "- Notice what they avoid or gloss over (but don't push)\n"
            "Still gentle and accepting. No pressure. Like a trusted friend who really listens.\n"
            "LISTENER GOAL: Understand their values, patterns, and emotional landscape."
        )
    else:
        return base + (
            "CURRENT PHASE: Incisive Questions. You now have rapport and can ask targeted, "
            "thought-provoking questions that reveal deeper patterns:\n"
            "- Questions about decisions and trade-offs ('if you had to choose between X and Y...')\n"
            "- Questions that challenge assumptions ('what would change if that weren't true?')\n"
            "- Questions about goals and desires ('what would your ideal version of that look like?')\n"
            "- Questions about group dynamics ('how do you usually handle disagreements?')\n"
            "- Hypothetical scenarios that reveal values ('what would you do if...?')\n"
            "These are INCISIVE questions — they remove limiting assumptions and reveal how "
            "the person truly thinks and feels. Ask naturally, not like an interview.\n"
            "LISTENER GOAL: Fill in the picture. Target areas you haven't explored yet."
        )
```

**Step 2: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_chatter_v2.py -v`
Expected: All 4 tests PASS

**Step 3: Commit**

```bash
git add eval_conversation.py
git commit -m "feat(v2.0): rewrite chatter with Deep Listening 10 Components"
```

---

### Task 3: Write test for reduced Chatter max_tokens

**Files:**
- Modify: `tests/test_chatter_v2.py`
- Reference: `eval_conversation.py:108-123` (Chatter class)

**Step 1: Write the failing test**

Add to `tests/test_chatter_v2.py`:

```python
def test_chatter_max_tokens_reduced():
    """V2.0: Chatter should use max_tokens=150 (down from 256) for shorter responses."""
    from unittest.mock import MagicMock, patch

    with patch("eval_conversation.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="That's interesting, tell me more.")]
        mock_client.messages.create.return_value = mock_response

        from eval_conversation import Chatter
        chatter = Chatter(api_key="test-key")
        chatter.next_message(
            conversation=[{"role": "speaker", "text": "I had a great weekend."}],
            turn_number=3,
            total_turns=20,
        )

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] <= 150, (
            f"Chatter max_tokens should be ≤150, got {call_kwargs['max_tokens']}"
        )
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_chatter_v2.py::test_chatter_max_tokens_reduced -v`
Expected: FAIL — current Chatter uses max_tokens=256

**Step 3: Commit test**

```bash
git add tests/test_chatter_v2.py
git commit -m "test: add failing test for chatter max_tokens reduction"
```

---

### Task 4: Reduce Chatter max_tokens from 256 to 150

**Files:**
- Modify: `eval_conversation.py:117-119` (inside `Chatter.next_message`)

**Step 1: Change max_tokens**

In `eval_conversation.py`, find the `Chatter.next_message` method and change `max_tokens=256` to `max_tokens=150`:

```python
        response = self._client.messages.create(
            model=self._model,
            max_tokens=150,  # V2.0: shorter to maximize speaker output
            system=system,
            messages=messages if messages else [{"role": "user", "content": "Start a casual conversation."}],
        )
```

**Step 2: Run tests**

Run: `.venv/bin/pytest tests/test_chatter_v2.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add eval_conversation.py
git commit -m "feat(v2.0): reduce chatter max_tokens to 150 for shorter responses"
```

---

### Task 5: Run V2.0 eval baseline (1 profile, 20 turns)

**Files:**
- Reference: `eval_conversation.py` (run_eval function)

**Step 1: Run a single-profile eval to establish V2.0 baseline**

```bash
cd /Users/michael/super-brain
ANTHROPIC_API_KEY=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 \
  .venv/bin/python eval_conversation.py 1 20
```

**Step 2: Record the result**

Note the MAE and save the output. Compare against V1.8 baseline (MAE 0.184).

**Step 3: Commit eval results if improved**

```bash
git add eval_conversation_results*.json
git commit -m "eval(v2.0): Deep Listening chatter baseline — MAE=X.XXX"
```

---

## V2.1 — Think Slow: Periodic Soul Extraction

### Task 6: Create ThinkSlowResult model

**Files:**
- Modify: `super_brain/models.py`
- Create: `tests/test_think_slow.py`

**Step 1: Write failing test for the model**

Create `tests/test_think_slow.py`:

```python
"""Tests for V2.1 Think Slow periodic extraction."""

from super_brain.models import ThinkSlowResult


def test_think_slow_result_creation():
    """ThinkSlowResult should hold partial profile, confidence map, and focus list."""
    from super_brain.models import PersonalityDNA, SampleSummary

    profile = PersonalityDNA(
        id="test",
        sample_summary=SampleSummary(
            total_tokens=0, conversation_count=0,
            date_range=["unknown", "unknown"],
            contexts=["test"], confidence_overall=0.5,
        ),
    )

    result = ThinkSlowResult(
        partial_profile=profile,
        confidence_map={"anxiety": 0.8, "trust": 0.3},
        low_confidence_traits=["trust"],
        observations=["Speaker avoids personal topics"],
    )

    assert result.low_confidence_traits == ["trust"]
    assert result.confidence_map["anxiety"] == 0.8
    assert len(result.observations) == 1


def test_think_slow_result_defaults():
    """ThinkSlowResult should have sensible defaults."""
    from super_brain.models import PersonalityDNA, SampleSummary

    profile = PersonalityDNA(
        id="test",
        sample_summary=SampleSummary(
            total_tokens=0, conversation_count=0,
            date_range=["unknown", "unknown"],
            contexts=["test"], confidence_overall=0.5,
        ),
    )

    result = ThinkSlowResult(
        partial_profile=profile,
        confidence_map={},
        low_confidence_traits=[],
        observations=[],
    )

    assert result.low_confidence_traits == []
    assert result.confidence_map == {}
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_think_slow.py -v`
Expected: FAIL — `ThinkSlowResult` doesn't exist yet

**Step 3: Commit test**

```bash
git add tests/test_think_slow.py
git commit -m "test: add failing tests for ThinkSlowResult model"
```

---

### Task 7: Implement ThinkSlowResult model

**Files:**
- Modify: `super_brain/models.py` (add at end)

**Step 1: Add ThinkSlowResult to models.py**

Append to `super_brain/models.py`:

```python
class ThinkSlowResult(BaseModel):
    """Result of periodic Think Slow extraction (V2.1).

    Produced every 5 conversation turns. Contains a partial personality
    estimate with per-trait confidence scores, enabling gap-aware conversation.
    """
    partial_profile: PersonalityDNA
    confidence_map: dict[str, float] = Field(default_factory=dict)
    low_confidence_traits: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
```

**Step 2: Run tests**

Run: `.venv/bin/pytest tests/test_think_slow.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add super_brain/models.py
git commit -m "feat(v2.1): add ThinkSlowResult model"
```

---

### Task 8: Write failing test for ThinkSlow extractor

**Files:**
- Create: `super_brain/think_slow.py`
- Modify: `tests/test_think_slow.py`

**Step 1: Write failing test for ThinkSlow.extract()**

Add to `tests/test_think_slow.py`:

```python
from unittest.mock import MagicMock, patch
import json


def test_think_slow_extract_returns_result():
    """ThinkSlow.extract() should return a ThinkSlowResult from conversation."""
    # Mock the LLM to return a valid Think Slow response
    mock_response_data = {
        "observations": [
            "Speaker uses short, direct sentences — possible low gregariousness",
            "Avoids emotional topics — possible low feelings openness",
        ],
        "trait_estimates": [
            {"dimension": "EXT", "name": "gregariousness", "value": 0.30, "confidence": 0.6},
            {"dimension": "OPN", "name": "feelings", "value": 0.35, "confidence": 0.4},
            {"dimension": "NEU", "name": "anxiety", "value": 0.50, "confidence": 0.3},
        ],
    }

    with patch("super_brain.think_slow.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text=json.dumps(mock_response_data))]
        mock_client.messages.create.return_value = mock_resp

        from super_brain.think_slow import ThinkSlow
        ts = ThinkSlow(api_key="test-key")

        conversation = [
            {"role": "chatter", "text": "How's your day going?"},
            {"role": "speaker", "text": "Fine."},
            {"role": "chatter", "text": "Do anything fun?"},
            {"role": "speaker", "text": "Not really. Just work."},
        ]

        result = ts.extract(conversation, focus_traits=None, previous=None)

        assert result.partial_profile is not None
        assert len(result.partial_profile.traits) == 3
        assert "anxiety" in result.confidence_map
        # Low confidence traits = those with confidence < 0.5
        assert "anxiety" in result.low_confidence_traits
        assert "feelings" in result.low_confidence_traits
        assert "gregariousness" not in result.low_confidence_traits  # confidence=0.6 >= 0.5


def test_think_slow_extract_with_focus_traits():
    """When focus_traits are provided, they should appear in the LLM prompt."""
    with patch("super_brain.think_slow.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text=json.dumps({
            "observations": [],
            "trait_estimates": [
                {"dimension": "SOC", "name": "social_dominance", "value": 0.50, "confidence": 0.5},
            ],
        }))]
        mock_client.messages.create.return_value = mock_resp

        from super_brain.think_slow import ThinkSlow
        ts = ThinkSlow(api_key="test-key")

        result = ts.extract(
            conversation=[{"role": "chatter", "text": "Hi"}, {"role": "speaker", "text": "Hello"}],
            focus_traits=["social_dominance", "humor_self_enhancing"],
            previous=None,
        )

        # Verify focus traits were mentioned in the prompt
        call_args = mock_client.messages.create.call_args
        user_msg = call_args[1]["messages"][0]["content"]
        assert "social_dominance" in user_msg
        assert "humor_self_enhancing" in user_msg
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_think_slow.py::test_think_slow_extract_returns_result -v`
Expected: FAIL — `super_brain.think_slow` doesn't exist

**Step 3: Commit test**

```bash
git add tests/test_think_slow.py
git commit -m "test: add failing tests for ThinkSlow extractor"
```

---

### Task 9: Implement ThinkSlow extractor

**Files:**
- Create: `super_brain/think_slow.py`

**Step 1: Implement ThinkSlow class**

```python
"""Think Slow: Periodic personality extraction during conversation (V2.1).

Runs every 5 conversation turns to build an incremental confidence map
of detected traits. This enables gap-aware conversation steering in V2.2.
"""

from __future__ import annotations

import json
import re

import anthropic

from super_brain.catalog import TRAIT_CATALOG, ALL_DIMENSIONS
from super_brain.models import (
    PersonalityDNA, Trait, SampleSummary, ThinkSlowResult, Evidence,
)


_THINK_SLOW_SYSTEM = """\
You are analyzing a conversation to extract personality signals about the target speaker \
(labeled "Person B"). This is a PERIODIC check — you may have limited data. Be honest \
about uncertainty.

For each trait you can estimate:
1. Note specific observations from the text
2. Give a value (0.0-1.0) and confidence (0.0-1.0)
3. Confidence should be LOW (0.1-0.3) if you have little evidence, MEDIUM (0.4-0.6) \
if you have some signals, HIGH (0.7-1.0) if you have clear, repeated evidence

Return ONLY valid JSON:
{
  "observations": ["observation 1", "observation 2", ...],
  "trait_estimates": [
    {"dimension": "<DIM>", "name": "<trait_name>", "value": <float>, "confidence": <float>}
  ]
}

IMPORTANT:
- Only estimate traits you have SOME evidence for. Skip traits with zero signal.
- Default value for uncertain traits is 0.45-0.55 (population mean).
- This is casual conversation — apply the same LLM bias corrections as standard detection.
- Be conservative: low confidence is better than wrong confidence.
"""


def _format_conversation(conversation: list[dict]) -> str:
    """Format conversation for Think Slow input."""
    lines = []
    for msg in conversation:
        label = "Person A" if msg["role"] == "chatter" else "Person B"
        lines.append(f"{label}: {msg['text']}")
    return "\n\n".join(lines)


def _build_focus_section(focus_traits: list[str] | None) -> str:
    """Build a focus section for traits that need more attention."""
    if not focus_traits:
        return ""

    trait_info = []
    for t in TRAIT_CATALOG:
        if t["name"] in focus_traits:
            trait_info.append(
                f"- {t['name']} ({t['dimension']}): {t['description']}\n"
                f"  detection_hint: {t['detection_hint']}"
            )

    if not trait_info:
        return ""

    return (
        "\n\nFOCUS TRAITS — these were low-confidence in previous extraction. "
        "Pay special attention to any signal (even weak) for:\n"
        + "\n".join(trait_info)
    )


class ThinkSlow:
    """Periodic personality extraction during conversation."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        kwargs: dict = {"api_key": api_key}
        if api_key.startswith("sk-or-"):
            kwargs["base_url"] = "https://openrouter.ai/api"
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model

    def extract(
        self,
        conversation: list[dict],
        focus_traits: list[str] | None = None,
        previous: ThinkSlowResult | None = None,
    ) -> ThinkSlowResult:
        """Extract personality signals from conversation so far.

        Args:
            conversation: Full conversation history.
            focus_traits: Traits to pay extra attention to (from previous low-confidence).
            previous: Previous ThinkSlowResult for anchoring.

        Returns:
            ThinkSlowResult with partial profile and confidence map.
        """
        conv_text = _format_conversation(conversation)
        focus_section = _build_focus_section(focus_traits)

        previous_section = ""
        if previous:
            prev_traits = {
                t.name: {"value": t.value, "confidence": previous.confidence_map.get(t.name, 0.5)}
                for t in previous.partial_profile.traits
            }
            previous_section = (
                f"\n\nPREVIOUS EXTRACTION (for anchoring — update, don't restart):\n"
                f"{json.dumps(prev_traits, indent=2)}"
            )

        user_message = (
            f"## Conversation\n\n{conv_text}\n\n"
            f"## Target Speaker\n\nAnalyze Person B's personality signals."
            f"{focus_section}{previous_section}\n\n"
            f"Return JSON with observations and trait_estimates."
        )

        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=_THINK_SLOW_SYSTEM,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = response.content[0].text
        data = _parse_think_slow_response(raw)

        # Build partial profile from estimates
        traits = []
        confidence_map: dict[str, float] = {}

        for est in data.get("trait_estimates", []):
            value = max(0.0, min(1.0, float(est["value"])))
            conf = max(0.0, min(1.0, float(est["confidence"])))
            traits.append(Trait(
                dimension=est["dimension"],
                name=est["name"],
                value=value,
                confidence=conf,
                evidence=[Evidence(text="think_slow", source="periodic_extraction")],
            ))
            confidence_map[est["name"]] = conf

        partial = PersonalityDNA(
            id="think_slow_partial",
            sample_summary=SampleSummary(
                total_tokens=len(conv_text.split()),
                conversation_count=1,
                date_range=["unknown", "unknown"],
                contexts=["think_slow"],
                confidence_overall=(
                    sum(confidence_map.values()) / max(len(confidence_map), 1)
                ),
            ),
            traits=traits,
        )

        low_conf = [name for name, conf in confidence_map.items() if conf < 0.5]

        return ThinkSlowResult(
            partial_profile=partial,
            confidence_map=confidence_map,
            low_confidence_traits=sorted(low_conf),
            observations=data.get("observations", []),
        )


def _parse_think_slow_response(raw: str) -> dict:
    """Parse Think Slow JSON response."""
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass

    return {"observations": [], "trait_estimates": []}
```

**Step 2: Run tests**

Run: `.venv/bin/pytest tests/test_think_slow.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add super_brain/think_slow.py
git commit -m "feat(v2.1): implement ThinkSlow periodic extraction"
```

---

### Task 10: Write failing test for Think Slow integration into conversation loop

**Files:**
- Modify: `tests/test_think_slow.py`
- Reference: `eval_conversation.py:837-871` (`simulate_conversation`)

**Step 1: Write failing test**

Add to `tests/test_think_slow.py`:

```python
def test_simulate_conversation_with_think_slow():
    """simulate_conversation should accept a ThinkSlow and extract every 5 turns."""
    from unittest.mock import MagicMock, patch, call
    import json

    mock_ts_response = json.dumps({
        "observations": ["test observation"],
        "trait_estimates": [
            {"dimension": "EXT", "name": "warmth", "value": 0.50, "confidence": 0.5},
        ],
    })

    with patch("eval_conversation.anthropic.Anthropic") as mock_anthropic, \
         patch("super_brain.think_slow.anthropic.Anthropic") as mock_ts_anthropic:

        # Mock Chatter + Speaker
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text="Test response")]
        mock_client.messages.create.return_value = mock_resp

        # Mock ThinkSlow
        mock_ts_client = MagicMock()
        mock_ts_anthropic.return_value = mock_ts_client
        mock_ts_resp = MagicMock()
        mock_ts_resp.content = [MagicMock(text=mock_ts_response)]
        mock_ts_client.messages.create.return_value = mock_ts_resp

        from eval_conversation import simulate_conversation, Chatter, PersonalitySpeaker
        from super_brain.think_slow import ThinkSlow
        from super_brain.profile_gen import generate_profile

        profile = generate_profile("test", seed=42)
        chatter = Chatter(api_key="test")
        speaker = PersonalitySpeaker(api_key="test")
        think_slow = ThinkSlow(api_key="test")

        conversation, ts_results = simulate_conversation(
            chatter, speaker, profile, n_turns=10, seed=0,
            think_slow=think_slow,
        )

        # Should have 2 ThinkSlow results (at turn 5 and turn 10)
        assert len(ts_results) == 2
        assert all(hasattr(r, "confidence_map") for r in ts_results)
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_think_slow.py::test_simulate_conversation_with_think_slow -v`
Expected: FAIL — `simulate_conversation` doesn't accept `think_slow` parameter

**Step 3: Commit test**

```bash
git add tests/test_think_slow.py
git commit -m "test: add failing test for ThinkSlow integration in conversation loop"
```

---

### Task 11: Integrate ThinkSlow into simulate_conversation

**Files:**
- Modify: `eval_conversation.py:837-871` (`simulate_conversation`)

**Step 1: Add ThinkSlow parameter and periodic extraction**

Replace the `simulate_conversation` function:

```python
def simulate_conversation(
    chatter: "Chatter",
    speaker: "PersonalitySpeaker",
    profile: PersonalityDNA,
    n_turns: int,
    seed: int = 0,
    think_slow: "ThinkSlow | None" = None,
) -> "list[dict] | tuple[list[dict], list]":
    """Simulate a natural conversation for n_turns exchanges.

    Args:
        think_slow: Optional ThinkSlow extractor. If provided, extracts every 5 turns
            and returns (conversation, think_slow_results).

    Returns:
        If think_slow is None: list of {"role": "chatter"|"speaker", "text": str}
        If think_slow is provided: (conversation, list[ThinkSlowResult])
    """
    import random as _random
    rng = _random.Random(seed)

    conversation: list[dict] = []
    ts_results: list = []
    previous_ts: "ThinkSlowResult | None" = None

    # Start with a random casual opener
    opener = rng.choice(CASUAL_OPENERS)
    conversation.append({"role": "chatter", "text": opener})

    # Speaker responds
    reply = speaker.respond(profile, conversation, turn_number=0)
    conversation.append({"role": "speaker", "text": reply})

    # Continue for n_turns - 1 more exchanges
    for turn in range(1, n_turns):
        # Chatter follows up naturally (with escalation)
        chatter_msg = chatter.next_message(conversation, turn_number=turn + 1, total_turns=n_turns)
        conversation.append({"role": "chatter", "text": chatter_msg})

        # Speaker responds in character
        speaker_reply = speaker.respond(profile, conversation, turn_number=turn)
        conversation.append({"role": "speaker", "text": speaker_reply})

        # Think Slow extraction every 5 turns
        if think_slow and (turn + 1) % 5 == 0:
            focus = previous_ts.low_confidence_traits if previous_ts else None
            ts_result = think_slow.extract(
                conversation=conversation,
                focus_traits=focus,
                previous=previous_ts,
            )
            ts_results.append(ts_result)
            previous_ts = ts_result

    if think_slow is not None:
        return conversation, ts_results
    return conversation
```

**Step 2: Run tests**

Run: `.venv/bin/pytest tests/test_think_slow.py -v`
Expected: All tests PASS

Also run existing tests to verify no regression:

Run: `.venv/bin/pytest tests/ -v --ignore=tests/test_closed_loop.py`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add eval_conversation.py
git commit -m "feat(v2.1): integrate ThinkSlow into conversation loop (every 5 turns)"
```

---

### Task 12: Run V2.1 eval with ThinkSlow

**Files:**
- Modify: `eval_conversation.py` (run_eval to use ThinkSlow)

**Step 1: Update run_eval to optionally use ThinkSlow**

In the `run_eval` function, after the existing `detector = Detector(api_key=api_key)` line, add:

```python
    from super_brain.think_slow import ThinkSlow
    think_slow = ThinkSlow(api_key=api_key)
```

Then update the `simulate_conversation` call:

```python
        conversation, ts_results = simulate_conversation(
            chatter, speaker, profile, n_turns=max_turns, seed=i,
            think_slow=think_slow,
        )
```

And add Think Slow logging after the conversation simulation:

```python
        # Log Think Slow confidence progression
        if ts_results:
            for idx, ts in enumerate(ts_results):
                n_estimated = len(ts.partial_profile.traits)
                n_low = len(ts.low_confidence_traits)
                avg_conf = (
                    sum(ts.confidence_map.values()) / max(len(ts.confidence_map), 1)
                )
                print(f"    ThinkSlow #{idx+1}: {n_estimated} traits estimated, "
                      f"{n_low} low-confidence, avg_conf={avg_conf:.2f}")
```

**Step 2: Run eval**

```bash
cd /Users/michael/super-brain
ANTHROPIC_API_KEY=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 \
  .venv/bin/python eval_conversation.py 1 20
```

**Step 3: Commit**

```bash
git add eval_conversation.py
git commit -m "eval(v2.1): ThinkSlow periodic extraction — MAE=X.XXX"
```

---

## V2.2 — Gap-Aware Chatter with Incisive Questions

### Task 13: Create trait_topic_map.py

**Files:**
- Create: `super_brain/trait_topic_map.py`
- Create: `tests/test_trait_topic_map.py`

**Step 1: Write failing test**

Create `tests/test_trait_topic_map.py`:

```python
"""Tests for trait → natural conversation topic mapping."""

from super_brain.trait_topic_map import TRAIT_TOPIC_MAP, get_topics_for_traits


def test_trait_topic_map_covers_stubborn_traits():
    """Map must cover the 5 stubbornly hard traits from EVAL_HISTORY."""
    stubborn = [
        "humor_self_enhancing",
        "social_dominance",
        "mirroring_ability",
        "information_control",
        "competence",
    ]
    for trait in stubborn:
        assert trait in TRAIT_TOPIC_MAP, f"Missing stubborn trait: {trait}"
        assert len(TRAIT_TOPIC_MAP[trait]) >= 2, f"Need ≥2 topics for {trait}"


def test_trait_topic_map_has_minimum_coverage():
    """Map should cover at least 30 traits (most impactful ones)."""
    assert len(TRAIT_TOPIC_MAP) >= 30


def test_get_topics_for_traits():
    """get_topics_for_traits should return natural conversation starters."""
    topics = get_topics_for_traits(["social_dominance", "trust"], max_per_trait=2)
    assert len(topics) >= 2
    assert len(topics) <= 4
    assert all(isinstance(t, str) for t in topics)
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_trait_topic_map.py -v`
Expected: FAIL — module doesn't exist

**Step 3: Commit test**

```bash
git add tests/test_trait_topic_map.py
git commit -m "test: add failing tests for trait topic map"
```

---

### Task 14: Implement trait_topic_map.py

**Files:**
- Create: `super_brain/trait_topic_map.py`

**Step 1: Implement the mapping**

```python
"""Map personality traits to natural conversation topics that reveal them (V2.2).

Each trait maps to 2-5 natural conversation topics/questions that would create
conditions for the trait to manifest — Incisive Questions from SoulMap Method.
These are NOT personality probes. They're natural conversation starters that
organically reveal specific traits.
"""

from __future__ import annotations

TRAIT_TOPIC_MAP: dict[str, list[str]] = {
    # ── Stubbornly hard traits (priority) ─────────────────────────────────
    "humor_self_enhancing": [
        "Have you ever had something go completely wrong but it turned out to be a blessing in disguise?",
        "What's the funniest thing that's happened to you recently — like something bad that you can laugh about now?",
        "How do you usually deal with a really bad day?",
    ],
    "social_dominance": [
        "When you're in a group project or team meeting, what role do you naturally take?",
        "How do you handle it when someone suggests a plan you think won't work?",
        "Tell me about a time you had to convince a group to go in a different direction.",
    ],
    "mirroring_ability": [
        "Do you find yourself picking up other people's accents or mannerisms?",
        "Are you the kind of person who adapts to different groups, or do you stay pretty much the same everywhere?",
        "How do you adjust when you're talking to someone very different from you?",
    ],
    "information_control": [
        "Are you pretty open with people or do you tend to keep things close to the chest?",
        "How much do you share about yourself when you first meet someone?",
        "Is there stuff about yourself that even your close friends don't know?",
    ],
    "competence": [
        "What's something you're really good at that you've had to work hard for?",
        "When you face a new challenge at work, how do you approach it?",
        "Tell me about a time you surprised yourself with how well you handled something.",
    ],

    # ── Dark traits ───────────────────────────────────────────────────────
    "narcissism": [
        "What's something you're proud of that other people might not know about?",
        "Do you think most people around you understand how capable you actually are?",
        "How do you feel when someone gets credit for something you did?",
    ],
    "machiavellianism": [
        "Do you think it's important to be strategic in how you deal with people at work?",
        "What's your take on office politics — necessary evil or just how things work?",
        "Have you ever had to navigate a tricky social situation to get what you needed?",
    ],
    "psychopathy": [
        "When someone comes to you with a personal problem, what's your instinct?",
        "How do you react when someone gets really emotional in front of you?",
        "Do you think people are too sensitive about things these days?",
    ],
    "sadism": [
        "Do you ever find yourself enjoying it when an arrogant person gets taken down a peg?",
        "What's your take on reality TV shows where people get eliminated?",
        "How do you feel about harsh roasts or dark humor?",
    ],

    # ── Emotional Architecture ────────────────────────────────────────────
    "emotional_granularity": [
        "When you're feeling off, can you usually pinpoint exactly what's bothering you?",
        "Do you find it easy to describe your emotions, or is it more like a general 'good' or 'bad'?",
    ],
    "emotional_regulation": [
        "When something really upsets you, what do you do to calm down?",
        "Do you find it easy to control your emotions in stressful situations?",
    ],
    "emotional_volatility": [
        "Would your friends say your moods change quickly, or are you pretty steady?",
        "Have you ever surprised yourself with a sudden mood shift?",
    ],
    "emotional_expressiveness": [
        "Are you the type of person whose face shows exactly what you're feeling?",
        "Do people usually know when something's bothering you, or are you good at hiding it?",
    ],
    "empathy_cognitive": [
        "Are you good at figuring out what someone's really feeling, even when they don't say it?",
        "When you watch a friend making a bad decision, do you understand why they're doing it?",
    ],
    "empathy_affective": [
        "When a friend is going through a tough time, how does it affect you personally?",
        "Do you find other people's emotions are contagious — like if they're sad, you feel sad?",
    ],

    # ── Social Dynamics ───────────────────────────────────────────────────
    "attachment_anxiety": [
        "In relationships, do you tend to worry about whether the other person cares as much as you do?",
        "How do you handle it when someone you're close to suddenly goes quiet?",
    ],
    "attachment_avoidance": [
        "Do you need a lot of alone time in relationships, or do you prefer constant closeness?",
        "How do you feel when someone gets really emotionally dependent on you?",
    ],
    "conflict_assertiveness": [
        "When someone says something you disagree with, do you speak up or let it go?",
        "Tell me about the last time you stood your ground in an argument.",
    ],
    "conflict_cooperativeness": [
        "When you have a disagreement with someone, is your first instinct to find a compromise?",
        "How important is it to you to keep the peace?",
    ],

    # ── Big Five Facets ───────────────────────────────────────────────────
    "anxiety": [
        "Are you a worrier, or do you tend to take things as they come?",
        "What keeps you up at night?",
    ],
    "trust": [
        "Do you give people the benefit of the doubt, or do they need to earn your trust?",
        "Have you been burned enough times that you're more careful now?",
    ],
    "warmth": [
        "Would you describe yourself as someone who gets close to people quickly?",
        "How do you show people you care about them?",
    ],
    "assertiveness": [
        "Are you comfortable speaking up in meetings, or do you prefer to listen first?",
        "When you want something, how do you go about getting it?",
    ],
    "self_discipline": [
        "How good are you at sticking to routines or habits?",
        "When you set yourself a goal, how often do you follow through?",
    ],
    "order": [
        "Are you the kind of person with lists and systems, or more go-with-the-flow?",
        "How organized would you say your daily life is?",
    ],
    "achievement_striving": [
        "What are you working toward right now?",
        "Are you someone who's always chasing the next thing, or more content with where you are?",
    ],
    "deliberation": [
        "When you have a big decision to make, do you research it carefully or go with your gut?",
        "Have you ever jumped into something without thinking and regretted it?",
    ],
    "gregariousness": [
        "Do you recharge by being around people or by having alone time?",
        "How often do you go out versus staying in?",
    ],
    "fantasy": [
        "Do you have a vivid imagination? Like daydreams or made-up scenarios?",
        "When you're bored, where does your mind wander?",
    ],
    "ideas": [
        "Do you enjoy abstract conversations — like debating ideas just for the sake of it?",
        "What's something you've been curious about lately?",
    ],
    "feelings": [
        "How in touch would you say you are with your emotions?",
        "Do you pay attention to how things make you feel, or do you just push through?",
    ],
    "values_openness": [
        "Are you the kind of person who challenges traditional ways of doing things?",
        "How do you feel about rules and conventions?",
    ],

    # ── Honesty-Humility ──────────────────────────────────────────────────
    "sincerity": [
        "Do you find it hard to fake enthusiasm for something?",
        "Would you rather be honest and hurt someone's feelings, or tell them what they want to hear?",
    ],
    "fairness": [
        "How important is playing fair to you, even when no one's watching?",
        "Have you ever been tempted to cut corners, and what did you do?",
    ],
    "humility_hexaco": [
        "Do you think you deserve special treatment, or are you pretty much like everyone else?",
        "How do you feel about people who act like they're better than others?",
    ],
    "modesty": [
        "When you accomplish something great, do you tell people about it?",
        "How do you react when someone compliments you?",
    ],

    # ── Humor ─────────────────────────────────────────────────────────────
    "humor_affiliative": [
        "Do you use humor a lot in your daily conversations?",
        "Would your friends say you're the funny one in the group?",
    ],
    "humor_aggressive": [
        "Do you enjoy teasing people, even if it's a bit edgy?",
        "What's your take on roast humor — funny or just mean?",
    ],
    "humor_self_defeating": [
        "Do you tend to make yourself the butt of the joke?",
        "When you mess up, do you make fun of yourself about it?",
    ],

    # ── Cognitive Style ───────────────────────────────────────────────────
    "need_for_cognition": [
        "Do you enjoy solving complex problems, or would you rather keep things simple?",
        "What's the last thing you really geeked out about?",
    ],
    "cognitive_flexibility": [
        "How easy is it for you to change your mind when you get new information?",
        "When someone challenges your opinion, what's your first reaction?",
    ],
    "locus_of_control": [
        "Do you feel like you're in control of what happens in your life?",
        "When things go wrong, do you tend to blame yourself or circumstances?",
    ],

    # ── Values ────────────────────────────────────────────────────────────
    "care_harm": [
        "When you see someone suffering, how does it affect you?",
        "Is compassion something you actively practice or more of a natural instinct?",
    ],
    "fairness_justice": [
        "How do you feel about inequality — is it just how the world works, or something that needs fixing?",
        "Tell me about a time you witnessed something unfair and what you did.",
    ],
    "loyalty_group": [
        "How loyal are you to your friend group or team? Like ride-or-die loyal?",
        "What would you do if a close friend did something you disagreed with?",
    ],
    "authority_respect": [
        "How do you feel about rules and authority figures?",
        "Do you respect the chain of command or think people should earn your respect?",
    ],

    # ── Interpersonal Strategy ────────────────────────────────────────────
    "hot_cold_oscillation": [
        "Do people ever say you're hard to read — warm one moment, distant the next?",
        "How consistent would you say your energy is with people?",
    ],
    "self_mythologizing": [
        "When you tell stories about your life, do you think you tend to make them more dramatic?",
        "Do your friends ever say you exaggerate?",
    ],
    "charm_influence": [
        "Are you good at getting people to go along with your ideas?",
        "How do you usually persuade someone who disagrees with you?",
    ],
}


def get_topics_for_traits(
    trait_names: list[str],
    max_per_trait: int = 1,
) -> list[str]:
    """Get natural conversation topics for a list of traits.

    Args:
        trait_names: Trait names to get topics for.
        max_per_trait: Maximum topics per trait.

    Returns:
        List of conversation topics/questions.
    """
    topics = []
    for name in trait_names:
        if name in TRAIT_TOPIC_MAP:
            topics.extend(TRAIT_TOPIC_MAP[name][:max_per_trait])
    return topics
```

**Step 2: Run tests**

Run: `.venv/bin/pytest tests/test_trait_topic_map.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add super_brain/trait_topic_map.py
git commit -m "feat(v2.2): add trait-to-topic map for incisive questions"
```

---

### Task 15: Write failing test for gap-aware Chatter

**Files:**
- Modify: `tests/test_chatter_v2.py`

**Step 1: Write failing test**

Add to `tests/test_chatter_v2.py`:

```python
def test_chatter_accepts_low_confidence_traits():
    """V2.2: _build_chatter_system should accept low_confidence_traits parameter."""
    from eval_conversation import _build_chatter_system

    # Should work with the new parameter
    prompt = _build_chatter_system(
        turn_number=16,
        total_turns=20,
        low_confidence_traits=["social_dominance", "humor_self_enhancing"],
    )

    # Late-phase prompt should include suggested topics for low-confidence traits
    assert "social_dominance" in prompt.lower() or "group" in prompt.lower() or "lead" in prompt.lower()


def test_chatter_gap_aware_early_phase_ignores_traits():
    """Early phase should NOT inject gap-aware topics (not enough rapport)."""
    from eval_conversation import _build_chatter_system

    prompt = _build_chatter_system(
        turn_number=3,
        total_turns=20,
        low_confidence_traits=["social_dominance", "humor_self_enhancing"],
    )

    # Early turns should not have suggested exploration topics
    assert "suggested" not in prompt.lower() or "exploration" not in prompt.lower()
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_chatter_v2.py::test_chatter_accepts_low_confidence_traits -v`
Expected: FAIL — `_build_chatter_system` doesn't accept `low_confidence_traits`

**Step 3: Commit test**

```bash
git add tests/test_chatter_v2.py
git commit -m "test: add failing tests for gap-aware chatter"
```

---

### Task 16: Add gap-aware topic injection to `_build_chatter_system`

**Files:**
- Modify: `eval_conversation.py:51` (`_build_chatter_system`)

**Step 1: Add low_confidence_traits parameter**

Update the function signature and the incisive questions phase:

```python
def _build_chatter_system(
    turn_number: int,
    total_turns: int,
    low_confidence_traits: list[str] | None = None,
) -> str:
    """Build a Chatter system prompt with Deep Listening + Incisive Questions.

    V2.0: Based on Nancy Kline's 10 Component Thinking Environment.
    V2.2: Gap-aware — uses low_confidence_traits to steer incisive questions.
    """
    # ... (keep existing base and early/deepening phases unchanged) ...
```

In the `else` branch (turn > 14), after the existing incisive questions section, add:

```python
    else:
        prompt = base + (
            "CURRENT PHASE: Incisive Questions. You now have rapport and can ask targeted, "
            "thought-provoking questions that reveal deeper patterns:\n"
            "- Questions about decisions and trade-offs ('if you had to choose between X and Y...')\n"
            "- Questions that challenge assumptions ('what would change if that weren't true?')\n"
            "- Questions about goals and desires ('what would your ideal version of that look like?')\n"
            "- Questions about group dynamics ('how do you usually handle disagreements?')\n"
            "- Hypothetical scenarios that reveal values ('what would you do if...?')\n"
            "These are INCISIVE questions — they remove limiting assumptions and reveal how "
            "the person truly thinks and feels. Ask naturally, not like an interview.\n"
            "LISTENER GOAL: Fill in the picture. Target areas you haven't explored yet."
        )

        # V2.2: Gap-aware topic injection
        if low_confidence_traits:
            from super_brain.trait_topic_map import get_topics_for_traits
            topics = get_topics_for_traits(low_confidence_traits[:5], max_per_trait=1)
            if topics:
                topic_lines = "\n".join(f"- {t}" for t in topics)
                prompt += (
                    f"\n\nSUGGESTED EXPLORATION DIRECTIONS (areas we haven't covered yet):\n"
                    f"{topic_lines}\n"
                    "Weave these naturally into conversation — don't fire them off like a questionnaire."
                )

        return prompt
```

**Step 2: Run tests**

Run: `.venv/bin/pytest tests/test_chatter_v2.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add eval_conversation.py
git commit -m "feat(v2.2): gap-aware chatter with incisive question targets"
```

---

### Task 17: Wire ThinkSlow confidence gaps into Chatter during conversation

**Files:**
- Modify: `eval_conversation.py` (`simulate_conversation`)

**Step 1: Pass low_confidence_traits from ThinkSlow to Chatter**

Update `simulate_conversation` to pass gap data into the Chatter's system prompt. In the conversation loop, after the ThinkSlow extraction, store the low-confidence traits and pass them to the Chatter on subsequent turns:

```python
    # Add before the for loop:
    current_low_conf: list[str] = []

    # In the for loop, update the chatter call:
        chatter_msg = chatter.next_message(
            conversation, turn_number=turn + 1, total_turns=n_turns,
            low_confidence_traits=current_low_conf if current_low_conf else None,
        )

    # After ThinkSlow extraction:
        if think_slow and (turn + 1) % 5 == 0:
            focus = previous_ts.low_confidence_traits if previous_ts else None
            ts_result = think_slow.extract(
                conversation=conversation,
                focus_traits=focus,
                previous=previous_ts,
            )
            ts_results.append(ts_result)
            previous_ts = ts_result
            current_low_conf = ts_result.low_confidence_traits
```

And update `Chatter.next_message` to accept and forward `low_confidence_traits`:

```python
    def next_message(
        self,
        conversation: list[dict],
        turn_number: int,
        total_turns: int,
        low_confidence_traits: list[str] | None = None,
    ) -> str:
        """Generate the next conversation message with phase-appropriate depth."""
        system = _build_chatter_system(
            turn_number, total_turns,
            low_confidence_traits=low_confidence_traits,
        )
        # ... rest unchanged ...
```

**Step 2: Run all tests**

Run: `.venv/bin/pytest tests/ -v --ignore=tests/test_closed_loop.py`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add eval_conversation.py
git commit -m "feat(v2.2): wire ThinkSlow gaps into chatter for targeted exploration"
```

---

### Task 18: Run V2.2 full eval

**Files:**
- Reference: `eval_conversation.py`

**Step 1: Run full eval (3 profiles, 20 turns)**

```bash
cd /Users/michael/super-brain
ANTHROPIC_API_KEY=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 \
  .venv/bin/python eval_conversation.py 3 20
```

**Step 2: Record results and compare**

Compare against:
- V1.8 baseline: MAE 0.184
- V2.0 target: MAE < 0.17
- V2.2 target: MAE < 0.15

**Step 3: Commit results**

```bash
git add eval_conversation_results*.json EVAL_HISTORY.md
git commit -m "eval(v2.2): gap-aware incisive questions — MAE=X.XXX"
```

---

### Task 19: Update EVAL_HISTORY.md with V2.0-V2.2 results

**Files:**
- Modify: `EVAL_HISTORY.md`

**Step 1: Add V2.0-V2.2 entries**

Append to EVAL_HISTORY.md with the actual MAE numbers from the eval runs:

```markdown
## V2.0 — Deep Listening Conversation Strategy
- Rewrote `_build_chatter_system()` with Nancy Kline's 10 Component Thinking Environment
- Phase split: turns 1-7 rapport, turns 8-14 deepening, turns 15+ incisive questions
- Reduced Chatter max_tokens from 256 to 150 (shorter prompts = more speaker output)
- MAE: X.XXX (was 0.184)

## V2.1 — Think Slow Periodic Extraction
- Added `ThinkSlow` class: periodic personality extraction every 5 turns
- Per-trait confidence map enables gap-aware conversation
- Integrated into `simulate_conversation`
- MAE: X.XXX

## V2.2 — Gap-Aware Incisive Questions
- Created `trait_topic_map.py`: 50+ traits → natural conversation topics
- `_build_chatter_system` reads ThinkSlow confidence gaps
- Incisive Questions phase (turn 15+) targets low-confidence traits
- MAE: X.XXX (target < 0.15)
```

**Step 2: Commit**

```bash
git add EVAL_HISTORY.md
git commit -m "docs: update EVAL_HISTORY with V2.0-V2.2 results"
```
