"""Think Fast: Rule-based signal detection for real-time conversation (V2.3).

Analyzes the LAST speaker response in a conversation to detect new facts,
conversational openings, and compute information entropy. No LLM calls —
pure regex patterns and heuristics.
"""

from __future__ import annotations

import re

from super_brain.models import ThinkFastResult


# ---------------------------------------------------------------------------
# Fact detection patterns
# ---------------------------------------------------------------------------

# Job / career patterns
_JOB_PATTERNS = [
    # "I'm a <job title>" / "I am a <job title>"
    re.compile(
        r"I(?:'m| am) (?:a |an )([\w\s]+?)(?:\.|,| at | in | for | and | who | with |$)",
        re.IGNORECASE,
    ),
    # "I work as a ..."
    re.compile(r"I work (?:as (?:a |an )?)(.+?)(?:\.|,| at | in | and |$)", re.IGNORECASE),
    # "I work at/for/in ..."
    re.compile(r"I work (?:at|for|in) (.+?)(?:\.|,| and |$)", re.IGNORECASE),
    # "work in <field>"
    re.compile(r"work in ([\w\s]+?)(?:\.|,| and |$)", re.IGNORECASE),
]

# Location patterns
_LOCATION_PATTERNS = [
    re.compile(r"(?:I live|I'm living|living|based|I'm based|moved to|moved from|from|in) ((?:[A-Z][\w]*(?:\s|$)){1,3})", re.MULTILINE),
    re.compile(r"(?:just )?moved to (.+?)(?:\.|,| from | and |$)", re.IGNORECASE),
    re.compile(r"(?:I'm |I am )?from (.+?)(?:\.|,| and |$)", re.IGNORECASE),
]

# Relationship / family patterns
_RELATIONSHIP_PATTERNS = [
    re.compile(r"\b(?:my )?(wife|husband|partner|girlfriend|boyfriend|fiancée?|spouse)\b", re.IGNORECASE),
    re.compile(r"\b(?:my )?(son|daughter|kids?|children|baby|toddler|mother|father|mom|dad|brother|sister|parents?)\b", re.IGNORECASE),
]

# Education patterns
_EDUCATION_PATTERNS = [
    re.compile(r"(?:I )?(?:studied|majored|graduated|got (?:my |a )?degree)(?: in| from)? (.+?)(?:\.|,| and |$)", re.IGNORECASE),
    re.compile(r"(?:I )?(?:went to|attend(?:ed)?) (.+?)(?:\.|,| and |$)", re.IGNORECASE),
]

# Hobby / interest patterns
_HOBBY_PATTERNS = [
    re.compile(r"I (?:love|enjoy|like|adore|am into|got into|'m into) ([\w\s]+?)(?:\.|,| and |$)", re.IGNORECASE),
    re.compile(r"(?:recently |just )?(?:started|got into|picked up|took up) ([\w\s]+?)(?:\.|,| and |$)", re.IGNORECASE),
]

# Age pattern
_AGE_PATTERNS = [
    re.compile(r"I(?:'m| am) (\d{1,2})(?:\b|,| year)", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Opening detection patterns — topics hinted at but not explored
# ---------------------------------------------------------------------------

_OPENING_PATTERNS = [
    re.compile(r"I(?:'ve| have) been thinking about (.+?)(?:\.|,| but | though|$)", re.IGNORECASE),
    re.compile(r"I(?:'d| would) (?:love|like|want) to (.+?)(?:\.|,| but | though|$)", re.IGNORECASE),
    re.compile(r"someday (?:I(?:'d| would) (?:love|like|want) to )?(.+?)(?:\.|,| but |$)", re.IGNORECASE),
    re.compile(r"I wish (.+?)(?:\.|,|$)", re.IGNORECASE),
    re.compile(r"(?:I'm |I am )?thinking (?:about|of) (.+?)(?:\.|,| but | though|$)", re.IGNORECASE),
    re.compile(r"(?:maybe |perhaps )?(?:one day|eventually) (.+?)(?:\.|,| but |$)", re.IGNORECASE),
    re.compile(r"I(?:'ve| have) always wanted to (.+?)(?:\.|,| but |$)", re.IGNORECASE),
    re.compile(r"haven't started (.+?)(?:\.|,| yet| but |$)", re.IGNORECASE),
]


def _extract_last_speaker_message(conversation: list[dict]) -> str | None:
    """Return the text of the last speaker message, or None if not found."""
    for msg in reversed(conversation):
        if msg.get("role") == "speaker":
            return msg.get("text", "")
    return None


def _detect_facts(text: str) -> list[str]:
    """Detect factual information from the text using regex patterns."""
    facts: list[str] = []
    seen: set[str] = set()

    pattern_groups = [
        ("job", _JOB_PATTERNS),
        ("location", _LOCATION_PATTERNS),
        ("relationship", _RELATIONSHIP_PATTERNS),
        ("education", _EDUCATION_PATTERNS),
        ("hobby", _HOBBY_PATTERNS),
        ("age", _AGE_PATTERNS),
    ]

    for category, patterns in pattern_groups:
        for pattern in patterns:
            for match in pattern.finditer(text):
                value = match.group(1).strip() if match.lastindex else match.group(0).strip()
                # Skip very short or generic matches
                if len(value) < 2:
                    continue
                key = f"{category}:{value.lower()}"
                if key not in seen:
                    seen.add(key)
                    facts.append(f"{category}: {value}")

    return facts


def _detect_opening(text: str) -> str | None:
    """Detect conversational openings — topics hinted at but not explored."""
    for pattern in _OPENING_PATTERNS:
        match = pattern.search(text)
        if match:
            captured = match.group(1).strip() if match.lastindex else match.group(0).strip()
            if len(captured) >= 3:
                return captured
    return None


def _compute_info_entropy(text: str, num_facts: int, has_opening: bool) -> float:
    """Compute 0-1 information entropy score based on heuristics.

    Scoring:
    - Word count: 50 words ~ 0.5 (linear scale)
    - Number of facts: +0.1 per fact, max +0.3
    - Opening detected: +0.1
    - Very short responses (<=5 words): capped at 0.2
    """
    words = text.split()
    word_count = len(words)

    # Base score from word count: 50 words = ~0.5
    base = min(word_count / 100.0, 0.5)

    # Fact bonus: +0.1 per fact, capped at +0.3
    fact_bonus = min(num_facts * 0.1, 0.3)

    # Opening bonus
    opening_bonus = 0.1 if has_opening else 0.0

    entropy = base + fact_bonus + opening_bonus

    # Very short responses capped at 0.2
    if word_count <= 5:
        entropy = min(entropy, 0.2)

    # Clamp to [0.0, 1.0]
    return max(0.0, min(1.0, entropy))


class ThinkFast:
    """Rule-based signal detection for real-time conversation analysis.

    Analyzes only the LAST speaker message in a conversation.
    No LLM calls — pure regex patterns and heuristics.
    """

    def analyze(self, conversation: list[dict]) -> ThinkFastResult:
        """Analyze the last speaker response for signals.

        Args:
            conversation: List of message dicts with 'role' and 'text' keys.

        Returns:
            ThinkFastResult with detected facts, openings, and entropy score.
        """
        if not conversation:
            return ThinkFastResult()

        text = _extract_last_speaker_message(conversation)
        if text is None:
            return ThinkFastResult()

        new_facts = _detect_facts(text)
        opening = _detect_opening(text)
        info_entropy = _compute_info_entropy(text, len(new_facts), opening is not None)

        return ThinkFastResult(
            new_facts=new_facts,
            opening=opening,
            info_entropy=info_entropy,
        )
