"""Typed provenance lineage (deepening #3; ADR-0004).

Provenance is a FIRST-CLASS typed structure, not a list of evidence-id strings.
Every AI narrative carries the full chain: operator query -> engine computation
-> knowledge layers -> source, with timestamps. The engine computation cites a
REAL OpportunityGroup id (deepening #1) and REAL ClosureEvent ids (deepening #2)
— never free strings.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from engine.opportunity_group import CycleStage  # reuse #1's enum — do NOT redefine

LtvCacBand = Literal["baseline", "target", "stretch"]
KnowledgeLayer = Literal["sector", "company", "customer"]
PrecedenceSource = Literal["sector", "company"]


class OperatorQueryRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query_id: str
    text: str
    role: str
    timestamp: str


class EngineComputationRef(BaseModel):
    """The engine step of the lineage — cites real #1 + #2 ids."""
    model_config = ConfigDict(extra="forbid")
    opportunity_group_ref: str            # REQUIRED — real OpportunityGroup id (#1)
    closure_event_refs: list[str]         # REQUIRED — real ClosureEvent ids (#2)
    cycle_stage: CycleStage
    ltv_cac_band: LtvCacBand
    timestamp: str


class KnowledgeLayerRef(BaseModel):
    model_config = ConfigDict(extra="forbid")
    layer: KnowledgeLayer
    source_id: str
    last_reviewed: Optional[str] = None


class PrecedenceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    precedence_source: PrecedenceSource
    overridden_by: Optional[str] = None
    override_reason: Optional[str] = None


class ProvenanceLineage(BaseModel):
    """The visible-by-default evidence chain for a narrative."""
    model_config = ConfigDict(extra="forbid")
    operator_query: OperatorQueryRef
    engine_computation: EngineComputationRef
    knowledge_layers: list[KnowledgeLayerRef] = Field(default_factory=list)
    sector_vs_company_precedence: Optional[PrecedenceRecord] = None
