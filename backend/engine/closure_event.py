"""ClosureEvent — the institutional-memory unit (deepening #2; ADR-0003).

A closure event is the typed, immutable record that an intervention was closed:
who claimed it, against which OpportunityGroup, and — when sector governance and
company knowledge disagree (doctrine Q4) — which precedence won and who, if
anyone, overrode it. It is the unit the company PKM cites.

`opportunity_group_ref` is REQUIRED: a closure with no cited OpportunityGroup is
an orphan and is refused. The OpportunityRelationship enum (from deepening #1)
drives the default precedence — defined once, reused here, never redefined.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from engine.opportunity_group import OpportunityRelationship  # reuse #1's enum — do NOT redefine

# Doctrine Q4: when sector governance and company knowledge disagree, sector wins
# by default; only a named actor may shift precedence to company.
PrecedenceSource = Literal["sector", "company"]


def precedence_from_relationship(rel: OpportunityRelationship) -> PrecedenceSource:
    """Default precedence implied by the cited group's relationship.

    A `shared` (universal, sector-governed) pool defaults to sector precedence;
    a clinic/company-specific `allocation` defaults to company; a `diagnostic`
    carries no pool, so sector governance is authoritative.
    """
    return "company" if rel == "allocation" else "sector"


def resolve_precedence(sector_position: str, company_position: str,
                       default: PrecedenceSource,
                       override_actor: Optional[str] = None,
                       override_reason: Optional[str] = None) -> dict:
    """Doctrine Q4 resolution.

    Agreement -> default precedence, single audit line.
    Disagreement -> default precedence (sector unless allocation), audit trail
    records BOTH positions. A named actor (with a reason) may override to the
    other source — that is the ONLY way precedence flips, and it is logged.
    """
    agree = sector_position == company_position
    audit: list[dict] = [
        {"source": "sector", "position": sector_position},
        {"source": "company", "position": company_position},
    ]
    precedence: PrecedenceSource = default
    overridden_by = None
    reason = None
    if not agree:
        audit.append({"event": "conflict", "default_precedence": default})
        if override_actor and override_reason:
            precedence = "company" if default == "sector" else "sector"
            overridden_by = override_actor
            reason = override_reason
            audit.append({"event": "named_actor_override", "actor": override_actor,
                          "reason": override_reason, "precedence": precedence})
        else:
            audit.append({"event": "escalation", "precedence": precedence,
                          "note": "sector precedence held; named-actor override required to flip"})
    return {"precedence_source": precedence, "overridden_by": overridden_by,
            "override_reason": reason, "audit_trail": audit, "conflict": not agree}


class ClosureEvent(BaseModel):
    """Immutable institutional-memory record of a closure. extra='forbid'."""

    model_config = ConfigDict(extra="forbid")

    closure_id: str
    intervention_id: str
    opportunity_group_ref: str            # REQUIRED — no orphan closures
    claim: dict
    proof: Optional[dict] = None
    precedence_source: PrecedenceSource = "sector"
    overridden_by: Optional[str] = None
    override_reason: Optional[str] = None
    timestamp: str
    audit_trail: list[dict] = Field(default_factory=list)
