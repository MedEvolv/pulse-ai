"""Typed AINarrative (deepening #3; ADR-0004).

The AI narrative is a validated structure, not a free string. It leads with the
binding constraint, carries a typed ProvenanceLineage (visible by default), a
named-owner handoff, a confidence drawn from a closed enum (no invented values),
and a hard human_approval_required gate. extra='forbid' — the model cannot smuggle
extra keys, ungrounded numbers, or invented confidence past this type.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from engine.provenance_lineage import ProvenanceLineage

Confidence = Literal["high", "medium", "low", "unverified"]


class NamedOwnerHandoff(BaseModel):
    """The named human who owns the next action (never the AI)."""
    model_config = ConfigDict(extra="forbid")
    owner_role: str
    owner_name: str
    action: str


class AINarrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str                                  # 1 sentence, binding-constraint lead
    summary: str                                   # 1-3 sentences
    provenance_lineage: ProvenanceLineage          # typed, first-class
    named_owner_handoff: NamedOwnerHandoff
    confidence: Confidence
    human_approval_required: Literal[True]         # always True — AI narrates, human acts
