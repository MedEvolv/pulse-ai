"""AINarrative generator (deepening #3; ADR-0004).

Deterministic by construction: the engine owns the numbers and the refs; the
narrative only renders them. The provenance lineage cites a REAL OpportunityGroup
id (#1, from cycle_compute) and REAL ClosureEvent ids (#2, from the spine) — so a
narrative can never point at a number or a closure that does not exist.

The optional `synthesized` mode (server-gated) lets a model rewrite only the
headline/summary prose; the lineage, refs, confidence and approval gate are
computed here and are never taken from the model.
"""
from __future__ import annotations

import hashlib
from typing import Optional

import engine
from engine import cycle_compute, sector_governance
from engine.ai_narrative import AINarrative, NamedOwnerHandoff
from engine.provenance_lineage import (
    EngineComputationRef, KnowledgeLayerRef, OperatorQueryRef,
    PrecedenceRecord, ProvenanceLineage,
)

# Deterministic named owner per region (named-owner handoff; never the AI).
_OWNER_NAME = {"REG-NORTH": "Ananya Mehra", "REG-WEST": "Priya Deshmukh", "REG-SOUTH": "Rohan Iyer"}


def _band(ltv_cac: float) -> str:
    """Map a sector LTV:CAC onto the three reference bands (clamps below-baseline)."""
    if ltv_cac < 3.0:
        return "baseline"
    if ltv_cac < 4.0:
        return "target"
    return "stretch"


def _query_id(region: str, sector: str, text: str) -> str:
    return "OQ-" + hashlib.sha256(f"{region}|{sector}|{text}".encode()).hexdigest()[:16]


def _binding_group(ct: dict, profile) -> Optional[dict]:
    """Pick the shared group at the sector's binding-constraint stage; else the
    lowest-value shared group (the visible drag)."""
    shared = [g for g in ct["groups"] if g["opportunity_relationship"] == "shared"]
    if not shared:
        return None
    if profile:
        at_stage = [g for g in shared if g["stage"] == profile.binding_constraint]
        if at_stage:
            return min(at_stage, key=lambda g: g["value_inr"])
    return min(shared, key=lambda g: g["value_inr"])


def build_narrative(region: str, sector: str, query_text: str, role: str,
                    spine, now_iso: str) -> AINarrative:
    """Deterministic AINarrative grounded in real #1 + #2 refs.

    Raises ValueError if the region has no shared opportunity pool (a narrative
    must cite a real OpportunityGroup — no orphan lineage).
    """
    profile = sector_governance.load_sector(sector)
    ct = cycle_compute.regional_total(region, sector)
    group = _binding_group(ct, profile)
    if group is None:
        raise ValueError(f"No shared opportunity pool in {region}; cannot ground a narrative.")

    opp_ref = group["opportunity_group_id"]
    stage = group["stage"]
    stage_label = profile.stage_label(stage) if profile else stage.title()
    band = _band(profile.ltv_cac if profile else 3.0)

    # Real ClosureEvent refs for this pool, from the append-only spine (#2).
    closure_refs = [e.closure_id for e in spine.all() if e.opportunity_group_ref == opp_ref]

    # Precedence (doctrine Q4) from the most recent matching closure event, if any.
    precedence = None
    matching = [e for e in spine.all() if e.opportunity_group_ref == opp_ref]
    if matching:
        last = matching[-1]
        precedence = PrecedenceRecord(
            precedence_source=last.precedence_source,
            overridden_by=last.overridden_by,
            override_reason=last.override_reason,
        )

    cadences = (profile.cadences if profile else {}) or {}
    owner_role = cadences.get("reactivation_owner", "Regional head")
    owner_name = _OWNER_NAME.get(region, "Regional head")
    reactivation = cadences.get("reactivation", "the sector reactivation cadence")

    lineage = ProvenanceLineage(
        operator_query=OperatorQueryRef(
            query_id=_query_id(region, sector, query_text),
            text=query_text or "Where is the flywheel leaking?",
            role=role, timestamp=now_iso,
        ),
        engine_computation=EngineComputationRef(
            opportunity_group_ref=opp_ref,
            closure_event_refs=closure_refs,
            cycle_stage=stage,
            ltv_cac_band=band,
            timestamp=now_iso,
        ),
        knowledge_layers=[
            KnowledgeLayerRef(layer="sector", source_id=f"sector:{sector}", last_reviewed=now_iso),
            KnowledgeLayerRef(layer="company", source_id=f"company:{region}", last_reviewed=now_iso),
        ],
        sector_vs_company_precedence=precedence,
    )

    headline_ltv = profile.ltv_cac if profile else 3.0
    headline = (f"{stage_label} is the binding constraint in "
                f"{engine.REGION_NAME.get(region, region)} - it caps the {sector} flywheel "
                f"at {headline_ltv:.1f}:1.")
    summary = (f"The single move: re-engage the {stage_label.lower()} pool with {owner_name} "
               f"via {reactivation}. Reference: sector:{sector}"
               + (f" + {len(closure_refs)} closure proof(s)" if closure_refs else "")
               + f", last reviewed {now_iso[:10]}.")

    return AINarrative(
        headline=headline,
        summary=summary,
        provenance_lineage=lineage,
        named_owner_handoff=NamedOwnerHandoff(
            owner_role=owner_role, owner_name=owner_name,
            action=f"Re-engage the {stage_label.lower()} pool via {reactivation}.",
        ),
        confidence="medium",   # deterministic ceiling — never claim 'high' without verification
        human_approval_required=True,
    )


def validate_refs(narrative: AINarrative, region: str, sector: str, spine) -> Optional[str]:
    """Reject orphan refs: the opportunity_group_ref must resolve to a real
    OpportunityGroup and every closure_event_ref to a real ClosureEvent.
    Returns a reason string if invalid, else None."""
    ec = narrative.provenance_lineage.engine_computation
    groups = cycle_compute.region_groups(region, sector)
    if not any(g.opportunity_group_id == ec.opportunity_group_ref for g in groups):
        return "ORPHAN_OPPORTUNITY_GROUP_REF"
    known = {e.closure_id for e in spine.all()}
    for ref in ec.closure_event_refs:
        if ref not in known:
            return "ORPHAN_CLOSURE_EVENT_REF"
    return None
