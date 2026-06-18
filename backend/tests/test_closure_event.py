"""Tests for the typed closure seam (deepening #2; ADR-0003/0004).

Covers the typed state machine, the ClosureEvent model (opportunity_group_ref
required), the doctrine-Q4 precedence rule (sector default + named-actor
override), the append-only spine (no mutation), and the POST /close route
(resolves a real OpportunityGroup, invalid transition rejected, orphan rejected).
"""
import pytest
from pydantic import ValidationError

import engine
from engine import intervention_state as ist
from engine.closure_event import ClosureEvent, precedence_from_relationship, resolve_precedence
from pkm.closure_event_spine import (
    AppendOnlyClosureEventSpine, InMemoryClosureEventSpine, build_closure_event_spine,
)


# --- typed state machine ---
def test_state_machine_transitions_and_terminal():
    S = ist.ClosureState
    assert ist.can_transition(S.PROOF_REQUIRED, S.CLOSURE_CLAIMED)
    assert ist.can_transition(S.CLOSURE_CLAIMED, S.CLOSED_VERIFIED)
    assert not ist.can_transition(S.PROOF_REQUIRED, S.CLOSED_VERIFIED)  # no skip
    with pytest.raises(ist.InvalidTransition):
        ist.validate_transition(S.CLOSED_VERIFIED, S.CLOSURE_CLAIMED)   # terminal


def test_closure_claim_uses_cycle_stage_enum():
    claim = ist.ClosureClaim(stage="retention", named_actor="Clinic manager", evidence_ids=["MEV-1"])
    assert claim.stage == "retention"
    with pytest.raises(ValidationError):
        ist.ClosureClaim(stage="contact", named_actor="x", evidence_ids=[])  # funnel name rejected


# --- ClosureEvent model ---
def test_opportunity_group_ref_is_required():
    ev = ClosureEvent(closure_id="CL-1", intervention_id="INT-0001",
                      opportunity_group_ref="OPP-REG-NORTH-SHOW-2026-06",
                      claim={}, timestamp="2026-06-19T00:00:00Z")
    assert ev.opportunity_group_ref
    with pytest.raises(ValidationError):
        ClosureEvent(closure_id="CL-2", intervention_id="INT-0002", claim={}, timestamp="t")
    with pytest.raises(ValidationError):  # extra=forbid
        ClosureEvent(closure_id="CL-3", intervention_id="INT-3",
                     opportunity_group_ref="X", claim={}, timestamp="t", rogue=1)


# --- doctrine Q4 precedence ---
def test_q4_sector_default_on_conflict_audit_shows_both():
    res = resolve_precedence("recall_due", "no_action", precedence_from_relationship("shared"))
    assert res["precedence_source"] == "sector"
    assert res["conflict"] is True
    sources = {a.get("source") for a in res["audit_trail"] if "source" in a}
    assert sources == {"sector", "company"}  # both positions recorded


def test_q4_named_actor_override_flips_precedence():
    res = resolve_precedence("recall_due", "no_action", "sector",
                             override_actor="Dr. Mehra (regional_head)",
                             override_reason="documented local exception")
    assert res["precedence_source"] == "company"
    assert res["overridden_by"] == "Dr. Mehra (regional_head)"
    assert any(a.get("event") == "named_actor_override" for a in res["audit_trail"])


# --- append-only spine ---
def test_spine_is_append_only_both_adapters():
    ev = ClosureEvent(closure_id="CL-1", intervention_id="INT-0001",
                      opportunity_group_ref="OPP-X", claim={}, timestamp="t")
    for spine in (InMemoryClosureEventSpine(), AppendOnlyClosureEventSpine()):
        eid = spine.append(ev)
        assert eid.startswith("CEV-")
        assert len(spine.get("INT-0001")) == 1
        assert len(spine.all()) == 1
        assert not hasattr(spine, "update") and not hasattr(spine, "delete")
    assert isinstance(build_closure_event_spine(), InMemoryClosureEventSpine)  # default (no DATABASE_URL)


# --- POST /close route ---
def _to_proof_required(client, headers):
    client.get("/api/interventions", headers=headers)
    items = client.get("/api/interventions", headers=headers).json()["interventions"]
    iv = next(i for i in items if i["status"] == "In Progress")
    r = client.patch(f"/api/interventions/{iv['intervention_id']}",
                     json={"status": "Proof Required"}, headers=headers)
    assert r.status_code == 200
    return iv["intervention_id"]


def test_close_route_records_closure_event(app_client, session_header):
    iid = _to_proof_required(app_client, session_header)
    ref = engine.region_opportunity_groups("REG-NORTH")[0]["opportunity_group_id"]
    r = app_client.post(f"/api/interventions/{iid}/close",
                        json={"opportunity_group_ref": ref, "named_actor": "Clinic manager",
                              "region": "REG-NORTH", "sector": "healthcare", "evidence_ids": ["MEV-1"]},
                        headers=session_header)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["closure_event"]["opportunity_group_ref"] == ref
    assert body["event_id"].startswith("CEV-")
    assert body["intervention"]["status"] == "Closure Claimed"


def test_close_route_rejects_orphan_ref(app_client, session_header):
    iid = _to_proof_required(app_client, session_header)
    r = app_client.post(f"/api/interventions/{iid}/close",
                        json={"opportunity_group_ref": "OPP-DOES-NOT-EXIST", "named_actor": "x",
                              "region": "REG-NORTH"}, headers=session_header)
    assert r.status_code == 422
