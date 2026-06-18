"""First-class OpportunityGroup type — the typed economic seam (ADR-0002).

The economic truth of the engine is a non-overlapping stage opportunity pool.
The `opportunity_relationship` enum decides what a group means for a total:

  * shared      — a regional opportunity pool. The ONLY thing additive in a
                  regional total.
  * allocation  — a sub-pool of a shared group (e.g. a clinic's share of the
                  regional show pool). Non-additive; informational drill-down.
  * diagnostic  — carries no recoverable pool (e.g. cost-per-attended). value 0,
                  no opportunity_group_id. Informational only.

This replaces the loose dicts that the leakage layer already tagged with
`opportunity_relationship`; here it is a validated, enforced model.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# The 5 universal cycle stages (sector-shaped names live in the governance YAML).
CycleStage = Literal["spend", "revenue", "retention", "expansion", "referral"]
OpportunityRelationship = Literal["shared", "allocation", "diagnostic"]


class OpportunityGroup(BaseModel):
    """A typed, non-overlapping stage opportunity pool. extra='forbid'."""

    model_config = ConfigDict(extra="forbid")

    opportunity_group_id: Optional[str] = None     # None only for diagnostic
    stage: CycleStage
    current_rate: Optional[float] = None
    benchmark_rate: Optional[float] = None
    raw_additional: float = 0.0
    display_additional: int = 0
    value_inr: int = 0
    metric_evidence_id: Optional[str] = None
    caveats: list[str] = Field(default_factory=list)
    opportunity_relationship: OpportunityRelationship

    @property
    def is_additive(self) -> bool:
        """Only shared groups contribute to a regional total."""
        return self.opportunity_relationship == "shared"


def shared_total(groups: list["OpportunityGroup"]) -> dict:
    """Sum ONLY the shared groups — the single source of additive truth."""
    shared = [g for g in groups if g.opportunity_relationship == "shared"]
    return {
        "shared_total_value_inr": sum(g.value_inr for g in shared),
        "shared_total_appointments": sum(g.display_additional for g in shared),
        "shared_group_count": len(shared),
        "filtered_group_count": len(groups) - len(shared),
    }
