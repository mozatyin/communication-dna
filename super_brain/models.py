"""Core data models for the Super Brain personality system."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """Supporting quote for a detected trait."""
    text: str
    source: str
    timestamp: Optional[str] = None


class Trait(BaseModel):
    """A single personality trait measurement on a 0.0-1.0 scale."""
    dimension: str          # e.g., "OPN", "CON", "DRK"
    name: str               # e.g., "fantasy", "narcissism"
    value: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(default_factory=list)


class TraitRelation(BaseModel):
    """Correlation between two traits."""
    source: str
    target: str
    correlation: float = Field(ge=-1.0, le=1.0)
    direction: str  # "positive", "negative", "conditional"


class SampleSummary(BaseModel):
    """Metadata about the text sample used for detection."""
    total_tokens: int = Field(ge=0)
    conversation_count: int = Field(ge=0)
    date_range: list[str]
    contexts: list[str]
    confidence_overall: float = Field(ge=0.0, le=1.0)


class PersonalityDNA(BaseModel):
    """Complete personality profile for one person — 66 traits across 13 dimensions."""
    id: str
    version: str = "0.1"
    created: Optional[datetime] = None
    updated: Optional[datetime] = None

    sample_summary: SampleSummary
    traits: list[Trait] = Field(default_factory=list)
    trait_relations: list[TraitRelation] = Field(default_factory=list)


class IncisiveQuestion(BaseModel):
    """A targeted question generated from Soul gaps to probe low-confidence traits."""
    question: str
    target: str
    priority: float = Field(default=0.5, ge=0.0, le=1.0)
    source: str = "trait_gap"


class ThinkSlowResult(BaseModel):
    """Result of periodic Think Slow extraction (V2.1).

    Produced every 5 conversation turns. Contains a partial personality
    estimate with per-trait confidence scores, enabling gap-aware conversation.
    """
    partial_profile: PersonalityDNA
    confidence_map: dict[str, float] = Field(default_factory=dict)
    low_confidence_traits: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    incisive_questions: list[IncisiveQuestion] = Field(default_factory=list)
    info_staleness: float = Field(ge=0.0, le=1.0, default=0.0)


class ThinkFastResult(BaseModel):
    """Real-time signal detection from a single conversational exchange.

    Produced after every exchange. Captures new facts, emotional shifts,
    contradictions, and conversational openings for the Conductor.
    """
    new_facts: list[str] = Field(default_factory=list)
    emotional_shift: Optional[str] = None
    contradiction: Optional[str] = None
    opening: Optional[str] = None
    info_entropy: float = Field(default=0.5, ge=0.0, le=1.0)


class ConductorAction(BaseModel):
    """Action selected by the Conductor to steer the conversation.

    Modes: listen (passive), follow_thread (continue topic),
    ask_incisive (probe a gap), push (challenge or redirect).
    """
    mode: str = Field(default="listen")
    context: str = Field(default="")
    question: Optional[str] = None


class Fact(BaseModel):
    """A factual piece of information about the person."""
    category: str       # "career", "relationship", "hobby", "education",
                        # "location", "family", "preference", "experience"
    content: str        # "software engineer at a startup"
    confidence: float = Field(ge=0.0, le=1.0)
    source_turn: int    # which turn this was extracted from


class Reality(BaseModel):
    """Current reality snapshot of the person's life situation."""
    summary: str                    # narrative: "Currently a mid-career engineer..."
    domains: dict[str, str]         # {"career": "...", "relationships": "..."}
    constraints: list[str]          # things limiting them
    resources: list[str]            # things they have going for them


class FactExtractionResult(BaseModel):
    """Result of a single FactExtractor cycle."""
    new_facts: list[Fact]           # facts found in this cycle
    reality: Reality | None = None  # updated reality snapshot
    secrets: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)


class Soul(BaseModel):
    """Full Soul model aggregating all layers of understanding about a person."""
    id: str

    # Layer 1: Character (existing 66-trait PersonalityDNA)
    character: PersonalityDNA

    # Layer 2: Facts (accumulated from FactExtractor)
    facts: list[Fact] = Field(default_factory=list)

    # Layer 3: Reality (latest snapshot from FactExtractor)
    reality: Reality | None = None

    # Cross-layer insights
    secrets: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
