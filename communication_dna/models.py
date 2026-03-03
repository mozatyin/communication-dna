"""Core data models for the Communication DNA system."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ContextOverride(BaseModel):
    """Feature value shift in a specific context."""
    value: float = Field(ge=0.0, le=1.0)
    intensity: float = Field(ge=0.0, le=1.0)


class Evidence(BaseModel):
    """Supporting sample for a detected feature."""
    text: str
    source: str
    timestamp: Optional[str] = None


class Feature(BaseModel):
    """A single communication style feature with its measurements."""
    dimension: str
    name: str
    value: float = Field(ge=0.0, le=1.0)
    intensity: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    usage_probability: float = Field(ge=0.0, le=1.0)
    stability: str = "stable"
    context_overrides: dict[str, ContextOverride] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)


class SignaturePattern(BaseModel):
    """Multi-feature co-activation pattern."""
    name: str
    features: list[str]
    co_occurrence: float = Field(ge=0.0, le=1.0)
    frequency: float = Field(ge=0.0, le=1.0)
    context: Optional[str] = None


class FeatureRelation(BaseModel):
    """Graph edge between two features."""
    source: str
    target: str
    correlation: float = Field(ge=-1.0, le=1.0)
    direction: str


class DepthTrigger(BaseModel):
    type: str
    effectiveness: float = Field(ge=0.0, le=1.0)


class DepthBarrier(BaseModel):
    type: str
    severity: float = Field(ge=0.0, le=1.0)


class DisclosureTrajectory(BaseModel):
    warmup_turns: int = Field(ge=0)
    plateau_depth: float = Field(ge=0.0, le=5.0)
    deepening_rate: float = Field(ge=0.0, le=1.0)


class DepthProfile(BaseModel):
    """User's self-disclosure depth characteristics."""
    baseline_depth: float = Field(ge=0.0, le=5.0)
    max_observed_depth: int = Field(ge=0, le=5)
    depth_triggers: list[DepthTrigger] = Field(default_factory=list)
    depth_barriers: list[DepthBarrier] = Field(default_factory=list)
    disclosure_trajectory: Optional[DisclosureTrajectory] = None


class SampleSummary(BaseModel):
    total_tokens: int = Field(ge=0)
    conversation_count: int = Field(ge=0)
    date_range: list[str]
    contexts: list[str]
    confidence_overall: float = Field(ge=0.0, le=1.0)


class CommunicationDNA(BaseModel):
    """Complete communication style profile for one person."""
    id: str
    version: str = "1.0"
    created: Optional[datetime] = None
    updated: Optional[datetime] = None

    sample_summary: SampleSummary
    features: list[Feature] = Field(default_factory=list)
    signature_patterns: list[SignaturePattern] = Field(default_factory=list)
    feature_relations: list[FeatureRelation] = Field(default_factory=list)
    context_variations: dict[str, dict] = Field(default_factory=dict)
    depth_profile: Optional[DepthProfile] = None
