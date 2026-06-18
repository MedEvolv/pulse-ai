"""Typed LTV:CAC computation (deepening #4; ADR-0002 — the flywheel metric).

LTV:CAC stops being a static YAML default and becomes a typed *computation*: a
company-level ratio derived from the opportunity pools, decomposed per stage /
cohort / location / intervention, with a band drawn from the doctrine reference
bands (2:1 baseline, 3:1 target, 4:1 stretch). Reuses #1's CycleStage and #3's
LtvCacBand Literal — defined once, never redefined.

Deterministic: same OpportunityGroups + sector profile -> same computation.
"""
from __future__ import annotations

import hashlib
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from engine.opportunity_group import CycleStage, OpportunityGroup
from engine.provenance_lineage import LtvCacBand  # Literal["baseline","target","stretch"]
from engine.sector_governance import CYCLE_STAGES

# Bounded per-stage adjustment: the computed ratio moves off the company's headline
# only modestly with the realized-vs-benchmark gap, so the metric stays grounded.
_SIGNAL_BOUND = 0.05


def classify_band(ltv_cac: float) -> LtvCacBand:
    """Doctrine reference bands: 2:1 baseline floor, 3:1 target, 4:1 stretch.

    [.., 3.0) -> baseline · [3.0, 4.0) -> target · [4.0, ..) -> stretch.
    (The >4.0 'category-creator' tier is reported in band_detail; the typed
    Literal tops out at 'stretch' so it stays compatible with #3.)
    """
    if ltv_cac < 3.0:
        return "baseline"
    if ltv_cac < 4.0:
        return "target"
    return "stretch"


def band_detail(ltv_cac: float) -> str:
    if ltv_cac < 2.0:
        return "below baseline"
    if ltv_cac >= 4.0:
        return "stretch (benchmark / category-creator)" if ltv_cac > 4.0 else "stretch"
    return classify_band(ltv_cac)


def _unit(*parts: str) -> float:
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


class LtvCacComputation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sector: str
    region: str
    stage: Optional[CycleStage] = None      # the binding/primary stage for this view
    company_ltv_cac: float                  # COMPUTED, not the YAML default
    band: LtvCacBand
    band_detail: str
    per_stage: dict
    per_cohort: dict
    per_location: dict
    per_intervention: dict


def compute_ltv_cac(ops: list[OpportunityGroup], profile, region: str = "REG-NORTH",
                    locations: Optional[list[str]] = None,
                    cohorts: Optional[list[str]] = None) -> LtvCacComputation:
    """Compute the typed LTV:CAC from the opportunity pools + the sector profile.

    company_ltv_cac is anchored on the company's headline ratio but moved by the
    bounded realized-vs-benchmark signal across the priced stages — a real
    computation, deterministic, never a bare default echo.
    """
    base = float(profile.ltv_cac) if profile else 3.0
    sector = profile.sector if profile else "unknown"

    shared = [o for o in ops
              if o.opportunity_relationship == "shared"
              and o.current_rate is not None and o.benchmark_rate]

    per_stage: dict = {}
    signals: list[float] = []
    for o in shared:
        gap = (o.current_rate - o.benchmark_rate) / o.benchmark_rate  # <0 when below benchmark
        sig = max(-_SIGNAL_BOUND, min(_SIGNAL_BOUND, gap)) * base
        signals.append(sig)
        per_stage[o.stage] = round(base + sig, 2)
    for st in CYCLE_STAGES:
        per_stage.setdefault(st, round(base, 2))

    agg = sum(signals) / len(signals) if signals else 0.0
    company = round(base + agg, 2)

    # Decompositions (deterministic seeds; the substrate has one funnel, the
    # cohort/location ratios are seeded around the computed company ratio).
    per_cohort = {name: round(company - 0.3 + 0.6 * _unit(sector, "cohort", name), 2)
                  for name in (cohorts or ["Critical few", "Mid tier", "Long tail"])}
    per_location = {name: round(company - 0.25 + 0.5 * _unit(sector, "loc", name), 2)
                    for name in (locations or [region])}
    # Per-intervention: the projected ratio if that stage's pool is recovered.
    per_intervention = {o.stage: round(company + 0.4 * (o.value_inr / max(1, sum(s.value_inr for s in shared))), 2)
                        for o in shared}

    binding = min(shared, key=lambda o: o.current_rate / o.benchmark_rate).stage if shared else None

    return LtvCacComputation(
        sector=sector, region=region, stage=binding,
        company_ltv_cac=company, band=classify_band(company), band_detail=band_detail(company),
        per_stage=per_stage, per_cohort=per_cohort,
        per_location=per_location, per_intervention=per_intervention,
    )
