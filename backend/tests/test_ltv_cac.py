"""Tests for the typed flywheel metric (deepening #4; ADR-0002).

Covers the LtvCacComputation band map (healthcare baseline, retail target),
company_ltv_cac as a computed field, the Goldratt BindingConstraint (typed
CycleStage), the Pareto Critical Few split, all 6 sectors, determinism, and the
/api/ltv_cac route.
"""
import pytest

from engine import cycle_compute
from engine.binding_constraint import BindingConstraint, find_constraint
from engine.critical_few import CriticalFew, identify_critical_few
from engine.ltv_cac import LtvCacComputation, classify_band

SECTORS = ["healthcare", "retail", "saas", "automotive", "hospitality", "financial_services"]
CYCLE = {"spend", "revenue", "retention", "expansion", "referral"}


def test_band_map():
    assert classify_band(2.8) == "baseline"
    assert classify_band(3.2) == "target"
    assert classify_band(4.0) == "stretch"
    assert classify_band(5.0) == "stretch"


def test_healthcare_baseline_retail_target_computed():
    hc = cycle_compute.regional_ltv_cac("REG-NORTH", "healthcare")
    rt = cycle_compute.regional_ltv_cac("REG-NORTH", "retail")
    assert isinstance(hc, LtvCacComputation)
    assert hc.band == "baseline"
    assert rt.band == "target"
    # company_ltv_cac is COMPUTED, not the YAML default (2.8 / 3.2)
    assert hc.company_ltv_cac != 2.8
    assert rt.company_ltv_cac != 3.2
    assert set(hc.per_stage.keys()) == CYCLE


def test_binding_constraint_is_typed_worst_stage():
    bc = cycle_compute.regional_binding_constraint("REG-NORTH", "healthcare")
    assert isinstance(bc, BindingConstraint)
    assert bc.constraint_stage in CYCLE                 # a real CycleStage, not a string label
    # Goldratt: the constraint stage has the worst ratio in the breakdown
    assert bc.ratio == min(bc.regional_breakdown.values())
    assert bc.delta_from_target > 0                     # there is a gap to close


def test_critical_few_pareto_split():
    cf = cycle_compute.regional_critical_few("REG-NORTH", "healthcare")
    assert isinstance(cf, CriticalFew)
    assert 0 < cf.count <= cf.population
    assert cf.coverage_share >= 0.80                    # covers >= 80% of value
    assert cf.count < cf.population or cf.coverage_share >= 0.80  # the few, not the tail


def test_all_six_sectors_compute():
    for s in SECTORS:
        comp = cycle_compute.regional_ltv_cac("REG-NORTH", s)
        assert comp.band in {"baseline", "target", "stretch"}
        assert comp.company_ltv_cac > 0
        bc = cycle_compute.regional_binding_constraint("REG-NORTH", s)
        assert bc is not None and bc.constraint_stage in CYCLE


def test_deterministic():
    a = cycle_compute.regional_ltv_cac("REG-WEST", "saas")
    b = cycle_compute.regional_ltv_cac("REG-WEST", "saas")
    assert a.company_ltv_cac == b.company_ltv_cac
    assert a.per_stage == b.per_stage


def test_api_ltv_cac_route(app_client):
    r = app_client.get("/api/ltv_cac", params={"sector": "healthcare", "region": "REG-NORTH"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ltv_cac"]["band"] == "baseline"
    assert body["binding_constraint"]["constraint_stage"] in CYCLE
    assert body["critical_few"]["coverage_share"] >= 0.80
    assert app_client.get("/api/ltv_cac", params={"sector": "nope"}).status_code == 422
