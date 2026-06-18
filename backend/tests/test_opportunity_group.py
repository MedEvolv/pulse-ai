"""Tests for the typed OpportunityGroup seam (ADR-0002).

Covers the Pydantic model (enums + extra=forbid), the cycle_compute waterfall
(shared-only summation, funnel->cycle mapping, parity with the substrate),
the sector governance adapter, the adversarial evaluation fixtures, and the
/api/sectors 5-cycle-stage exposure.
"""
import pytest
from pydantic import ValidationError

import engine
import evaluation
from engine import cycle_compute, sector_governance
from engine.opportunity_group import OpportunityGroup, shared_total

CYCLE = {"spend", "revenue", "retention", "expansion", "referral"}


# --- the typed model ---
def test_model_enforces_stage_enum_and_extra_forbid():
    g = OpportunityGroup(stage="spend", opportunity_relationship="shared", value_inr=100)
    assert g.is_additive is True
    with pytest.raises(ValidationError):
        OpportunityGroup(stage="contact", opportunity_relationship="shared")  # funnel name rejected
    with pytest.raises(ValidationError):
        OpportunityGroup(stage="spend", opportunity_relationship="made_up")
    with pytest.raises(ValidationError):
        OpportunityGroup(stage="spend", opportunity_relationship="shared", bogus_field=1)


def test_shared_total_filters_allocation_and_diagnostic():
    groups = [
        OpportunityGroup(stage="spend", opportunity_relationship="shared", value_inr=100, display_additional=5),
        OpportunityGroup(stage="retention", opportunity_relationship="allocation", value_inr=90, display_additional=4),
        OpportunityGroup(stage="revenue", opportunity_relationship="diagnostic", value_inr=0),
    ]
    t = shared_total(groups)
    assert t["shared_total_value_inr"] == 100
    assert t["shared_group_count"] == 1
    assert t["filtered_group_count"] == 2


# --- cycle_compute over the real engine ---
def test_cycle_compute_maps_funnel_to_cycle_and_matches_substrate():
    ct = cycle_compute.regional_total("REG-NORTH", "healthcare")
    shared = [g for g in ct["groups"] if g["opportunity_relationship"] == "shared"]
    assert shared, "expected at least one shared pool"
    assert all(g["stage"] in CYCLE for g in ct["groups"])
    # parity: typed shared total == substrate scenario value (no double counting)
    sub = engine.regional_opportunity_summary("REG-NORTH")
    assert ct["shared_total_value_inr"] == sub["scenario_value_inr"]
    # provenance names both adapters
    assert set(ct["provenance"]["adapters"]) == {"deterministic_engine", "sector_governance_yaml"}


def test_cycle_compute_is_deterministic():
    a = cycle_compute.regional_total("REG-SOUTH")
    b = cycle_compute.regional_total("REG-SOUTH")
    assert a["shared_total_value_inr"] == b["shared_total_value_inr"]
    assert [g["stage"] for g in a["groups"]] == [g["stage"] for g in b["groups"]]


# --- sector governance adapter (the second adapter) ---
def test_sector_governance_loads_typed_profile_for_all_six():
    for sid in sector_governance.list_sectors():
        p = sector_governance.load_sector(sid)
        assert p is not None
        assert p.cycle_stages() == ["spend", "revenue", "retention", "expansion", "referral"]
        assert p.binding_constraint in CYCLE
        assert p.stage_label("retention")  # non-empty sector-shaped label
    assert sector_governance.load_sector("does-not-exist") is None


# --- adversarial fixtures ---
def test_opportunity_fixtures_all_pass():
    res = evaluation.run_opportunity_fixtures()
    assert res["failed"] == 0, res["failed_case_ids"]
    assert res["scenario_count"] >= 5


# --- API exposes 5 cycle stages per sector ---
def test_api_sectors_returns_five_cycle_stages(app_client):
    body = app_client.get("/api/sectors").json()
    assert len(body["sectors"]) == 6
    for s in body["sectors"]:
        assert len(s["cycle_stages"]) == 5
        assert [c["stage"] for c in s["cycle_stages"]] == \
            ["spend", "revenue", "retention", "expansion", "referral"]
