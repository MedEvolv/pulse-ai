"""5-stage cycle waterfall over the deterministic engine — typed seam (ADR-0002).

Maps the substrate's acquisition funnel (contact / booking / show) onto the 5
universal cycle stages and emits typed OpportunityGroups. Sector-shaped stage
labels come from the sector governance adapter (the second adapter).

Only `shared` groups contribute to a regional total. `allocation` (clinic
sub-pools) and `diagnostic` (cost-per-attended) are filtered out of the sum.

Deterministic: reuses engine.region_opportunity_groups (lru_cached, seed-based),
so the typed shared-total equals the substrate total — no double counting, the
single source of additive truth.
"""
from __future__ import annotations

import engine
from engine import sector_governance
from engine.opportunity_group import OpportunityGroup, shared_total

# The substrate funnel maps onto the first three cycle stages. Expansion and
# referral have no synthetic catalogue yet (a v1.1 commitment) — no shared pool
# is emitted for them, rather than fabricating one.
FUNNEL_TO_CYCLE = {"contact": "spend", "booking": "revenue", "show": "retention"}


def region_groups(region: str, sector: str = "healthcare") -> list:
    """Typed OpportunityGroups for a region.

    shared      — the non-overlapping regional pools (the only additive ones)
    allocation  — clinic shares of the regional SHOW pool (non-additive)
    """
    groups: list[OpportunityGroup] = []

    for g in engine.region_opportunity_groups(region):
        groups.append(OpportunityGroup(
            opportunity_group_id=g["opportunity_group_id"],
            stage=FUNNEL_TO_CYCLE[g["stage"]],
            current_rate=g["current_rate"],
            benchmark_rate=g["benchmark_rate"],
            raw_additional=g["raw_additional_attended"],
            display_additional=g["display_additional_attended"],
            value_inr=g["value_inr"],
            metric_evidence_id=g["metric_evidence_id"],
            caveats=list(g["caveats"]),
            opportunity_relationship="shared",
        ))

    for _code, a in engine.clinic_show_allocation(region).items():
        groups.append(OpportunityGroup(
            opportunity_group_id=a["opportunity_group_id"],
            stage=FUNNEL_TO_CYCLE["show"],
            current_rate=None,
            benchmark_rate=None,
            raw_additional=float(a["display_additional_attended"]),
            display_additional=a["display_additional_attended"],
            value_inr=a["value_inr"],
            metric_evidence_id=a["metric_evidence_id"],
            caveats=list(a["caveats"]),
            opportunity_relationship="allocation",
        ))

    return groups


def regional_total(region: str, sector: str = "healthcare") -> dict:
    """Sum ONLY shared groups (the waterfall). Allocation + diagnostic filtered.

    Returns a typed, provenance-bearing summary. The total equals the substrate
    regional_opportunity_summary total by construction.
    """
    groups = region_groups(region, sector)
    profile = sector_governance.load_sector(sector)
    totals = shared_total(groups)
    return {
        "region_id": region,
        "sector": sector,
        **totals,
        "groups": [g.model_dump() for g in groups],
        "stage_labels": (profile.stage_labels if profile else {}),
        "provenance": {
            "adapters": ["deterministic_engine", "sector_governance_yaml"],
            "rule_version": engine.RULE_VERSION,
            "period": engine.PERIOD,
            "note": "Only opportunity_relationship == 'shared' contributes to the total.",
        },
    }


def cycle_stages_for(sector: str = "healthcare") -> list:
    """The 5 cycle stages with sector-shaped labels, for the API/flywheel."""
    profile = sector_governance.load_sector(sector)
    stages = sector_governance.CYCLE_STAGES
    return [{"stage": s, "label": (profile.stage_label(s) if profile else s.title())}
            for s in stages]
