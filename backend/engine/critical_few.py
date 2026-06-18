"""Typed Critical Few (deepening #4; ADR-0002 — Pareto 20/80).

The Critical Few are the smallest set of opportunity pools that drive ~80% of the
recoverable value — the handful the AI narrative surfaces, not the long tail.
Reusable across all 6 sectors (operates on typed OpportunityGroups).
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from engine.opportunity_group import OpportunityGroup

PARETO_THRESHOLD = 0.80


class CriticalFew(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[dict]              # the critical-few pools (ref, stage, value, share)
    count: int                     # size of the critical few
    population: int                # total shared pools considered
    total_value_inr: int
    coverage_share: float          # fraction of total value the critical few cover


def identify_critical_few(ops: list[OpportunityGroup],
                          threshold: float = PARETO_THRESHOLD) -> CriticalFew:
    """Smallest set of shared pools whose cumulative value >= threshold of total."""
    shared = sorted(
        [o for o in ops if o.opportunity_relationship == "shared"],
        key=lambda o: o.value_inr, reverse=True,
    )
    total = sum(o.value_inr for o in shared)

    items: list[dict] = []
    cum = 0
    for o in shared:
        cum += o.value_inr
        items.append({
            "opportunity_group_ref": o.opportunity_group_id,
            "stage": o.stage,
            "value_inr": o.value_inr,
            "share": round(o.value_inr / total, 4) if total else 0.0,
        })
        if total and cum / total >= threshold:
            break

    return CriticalFew(
        items=items,
        count=len(items),
        population=len(shared),
        total_value_inr=total,
        coverage_share=round(cum / total, 4) if total else 0.0,
    )
