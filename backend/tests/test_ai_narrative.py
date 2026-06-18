"""Tests for the typed AINarrative seam (deepening #3; ADR-0004).

Covers the typed model (6 fields, extra=forbid, confidence enum, approval gate),
the typed provenance lineage citing real #1 + #2 refs, the deterministic
generator, orphan-ref rejection, the use_model budget gate (default off), and the
POST /api/narrative route (deterministic default, synthesized opt-in, orphan/empty
rejection).
"""
import pytest
from pydantic import ValidationError

import model_budget
from engine import ai_evidence
from engine.ai_narrative import AINarrative, NamedOwnerHandoff
from engine.provenance_lineage import ProvenanceLineage
from pkm.closure_event_spine import InMemoryClosureEventSpine
from engine.closure_event import ClosureEvent

NOW = "2026-06-19T10:00:00Z"


def _narr(spine):
    return ai_evidence.build_narrative("REG-NORTH", "healthcare", "Where is the leak?",
                                       "regional_head", spine, NOW)


# --- typed model ---
def test_ai_narrative_enforces_enum_extra_forbid_and_approval():
    n = _narr(InMemoryClosureEventSpine())
    assert isinstance(n, AINarrative) and isinstance(n.provenance_lineage, ProvenanceLineage)
    base = dict(headline="h", summary="s", provenance_lineage=n.provenance_lineage,
                named_owner_handoff=n.named_owner_handoff)
    with pytest.raises(ValidationError):   # invented confidence
        AINarrative(**base, confidence="amazing", human_approval_required=True)
    with pytest.raises(ValidationError):   # approval gate must be True
        AINarrative(**base, confidence="high", human_approval_required=False)
    with pytest.raises(ValidationError):   # extra=forbid
        AINarrative(**base, confidence="high", human_approval_required=True, rogue=1)


# --- deterministic generator grounds real refs ---
def test_narrative_provenance_cites_real_opportunity_group():
    spine = InMemoryClosureEventSpine()
    n = _narr(spine)
    ec = n.provenance_lineage.engine_computation
    assert ec.opportunity_group_ref  # real id from cycle_compute
    assert ec.cycle_stage in {"spend", "revenue", "retention", "expansion", "referral"}
    assert ec.ltv_cac_band in {"baseline", "target", "stretch"}
    assert ai_evidence.validate_refs(n, "REG-NORTH", "healthcare", spine) is None
    assert n.confidence == "medium"  # deterministic ceiling, never 'high'


def test_narrative_includes_real_closure_event_refs():
    spine = InMemoryClosureEventSpine()
    n0 = _narr(spine)
    opp = n0.provenance_lineage.engine_computation.opportunity_group_ref
    ev = ClosureEvent(closure_id="CL-INT-0002-x", intervention_id="INT-0002",
                      opportunity_group_ref=opp, claim={}, timestamp=NOW)
    spine.append(ev)
    n1 = _narr(spine)
    assert "CL-INT-0002-x" in n1.provenance_lineage.engine_computation.closure_event_refs
    assert ai_evidence.validate_refs(n1, "REG-NORTH", "healthcare", spine) is None


def test_validate_refs_rejects_orphans():
    spine = InMemoryClosureEventSpine()
    n = _narr(spine)
    # tamper with an orphan closure ref
    n.provenance_lineage.engine_computation.closure_event_refs = ["CL-DOES-NOT-EXIST"]
    assert ai_evidence.validate_refs(n, "REG-NORTH", "healthcare", spine) == "ORPHAN_CLOSURE_EVENT_REF"
    n.provenance_lineage.engine_computation.opportunity_group_ref = "OPP-NONE"
    assert ai_evidence.validate_refs(n, "REG-NORTH", "healthcare", spine) == "ORPHAN_OPPORTUNITY_GROUP_REF"


# --- budget gate ---
def test_use_model_mode_default_off_and_synthesized_degrades():
    assert model_budget.use_model_mode() == "off"
    assert model_budget.use_model_mode("garbage") == "off"
    # MODEL_ENABLED is false in tests -> synthesized degrades to deterministic (no spend)
    assert model_budget.use_model_mode("synthesized") == "deterministic"
    assert model_budget.config()["use_model_default"] == "off"


# --- API route ---
def test_api_narrative_deterministic_default(app_client, session_header):
    r = app_client.post("/api/narrative",
                        json={"region": "REG-NORTH", "sector": "healthcare",
                              "question": "Where is the flywheel leaking?"},
                        headers=session_header)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["served_mode"] == "deterministic"
    assert body["requested_mode"] == "off"
    n = body["narrative"]
    assert n["human_approval_required"] is True
    assert n["confidence"] in {"high", "medium", "low", "unverified"}
    assert n["provenance_lineage"]["engine_computation"]["opportunity_group_ref"]


def test_api_narrative_synthesized_opt_in_degrades_when_model_off(app_client, session_header):
    r = app_client.post("/api/narrative",
                        json={"region": "REG-NORTH", "use_model": "synthesized"},
                        headers=session_header)
    assert r.status_code == 200
    # opt-in requested, but model disabled in tests -> served deterministic, no spend
    assert r.json()["served_mode"] == "deterministic"


def test_api_narrative_rejects_unknown_sector(app_client, session_header):
    r = app_client.post("/api/narrative",
                        json={"region": "REG-NORTH", "sector": "nope"},
                        headers=session_header)
    assert r.status_code == 422
