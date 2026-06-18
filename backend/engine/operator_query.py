"""Typed OperatorQuery (deepening #5; ADR-0003).

The operator-facing "Ask [Company]:" surface is a pre-canned library, not a
free-text box (v1.0). Each question is a typed OperatorQuery bound to a sector,
a cycle stage (#1's CycleStage), and an answer domain that routes to a typed
computation (#4) or the closure history (#2). extra='forbid'.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from engine.opportunity_group import CycleStage  # reuse #1's enum — do NOT redefine

# The 5 answer domains a pre-canned question can resolve to.
AnswerType = Literal["ltv_cac", "binding_constraint", "critical_few", "closure_history", "narrative"]


class OperatorQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str
    query_text: str
    sector: str
    stage: CycleStage
    answer_type: AnswerType
    pre_canned: bool = True
    related: list[str] = Field(default_factory=list)
