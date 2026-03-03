"""Core data models for the Intention Graph system."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """Supporting quote from dialogue for an extracted intention."""
    quote: str
    utterance_index: int = Field(ge=0)
    speaker: str = ""


class ActionNode(BaseModel):
    """A single node in the intention graph — a concrete behavioral intention."""
    id: str
    text: str
    domain: str
    source: Literal["expressed", "inferred"]
    status: Literal["pending", "completed"]
    confidence: float = Field(ge=0.0, le=1.0)
    specificity: float = Field(ge=0.0, le=1.0)
    evidence: list[Evidence] = Field(default_factory=list)
    completed_at: Optional[datetime] = None


class Transition(BaseModel):
    """A directed edge in the intention graph — transition probability between actions."""
    from_id: str
    to_id: str
    base_probability: float = Field(ge=0.0, le=1.0)
    dna_adjusted_probability: float = Field(ge=0.0, le=1.0)
    relation: Literal[
        "next_step",
        "decomposes_to",
        "alternative",
        "enables",
        "evolves_to",
    ]
    confidence: float = Field(ge=0.0, le=1.0)


class Ambiguity(BaseModel):
    """An ambiguous branch point in the graph requiring clarification."""
    node_id: str
    branches: list[str]
    incisive_question: str
    information_gain: float = Field(ge=0.0, le=1.0)


class GraphSnapshot(BaseModel):
    """A snapshot of graph evolution at a point in time."""
    timestamp: datetime
    trigger: str
    added_nodes: list[str] = Field(default_factory=list)
    removed_nodes: list[str] = Field(default_factory=list)
    new_end_goal: Optional[str] = None


class IntentionGraph(BaseModel):
    """Complete probabilistic intention graph for one person."""
    nodes: list[ActionNode] = Field(default_factory=list)
    transitions: list[Transition] = Field(default_factory=list)
    end_goal: Optional[str] = None
    dna_profile_id: Optional[str] = None
    completed_path: list[str] = Field(default_factory=list)
    evolution_history: list[GraphSnapshot] = Field(default_factory=list)
    ambiguities: list[Ambiguity] = Field(default_factory=list)
    summary: str = ""
