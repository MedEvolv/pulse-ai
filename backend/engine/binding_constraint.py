"""Typed BindingConstraint (deepening #4; ADR-0002 — Goldratt's Theory of Constraints).

The binding constraint is the one cycle stage that, improved, would move the
headline LTV:CAC the most — computed as the worst current/benchmark ratio across
the priced stages, NOT a sector label string. Cites a real CycleStage (#1).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict

from engine.opportunity_group import CycleStage, OpportunityGroup

TARGET_RATIO = 1.0  # benchmark parity: a stage at/above benchmark is not the constraint


class BindingConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    constraint_stage: CycleStage          # real cycle stage, not a string
    ratio: float                          # current / benchmark at the constraint
    delta_from_target: float              # benchmark_rate - current_rate (the gap to close)
    regional_breakdown: dict              # stage -> ratio, the whole flywheel


def find_constraint(ops: list[OpportunityGroup]) -> Optional[BindingConstraint]:
    """Goldratt: the stage with the worst current/benchmark ratio is the binding
    constraint. Returns None if no priced stage carries both rates."""
    shared = [o for o in ops
              if o.opportunity_relationship == "shared"
              and o.current_rate is not None and o.benchmark_rate]
    if not shared:
        return None

    ratios = {o.stage: o.current_rate / o.benchmark_rate for o in shared}
    worst_stage = min(ratios, key=ratios.get)
    worst = next(o for o in shared if o.stage == worst_stage)

    return BindingConstraint(
        constraint_stage=worst_stage,
        ratio=round(ratios[worst_stage], 4),
        delta_from_target=round(worst.benchmark_rate - worst.current_rate, 4),
        regional_breakdown={st: round(r, 4) for st, r in ratios.items()},
    )
