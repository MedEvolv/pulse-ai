"""Tests for the RevOpsOS v1.0 sector layer (backend/sectors.py + endpoints).

Covers: all 6 profiles load, the coercion produces one canonical shape, the 5
universal cycle stages render with sector names, the binding constraint is the
weakest stage, LTV:CAC bands resolve, and determinism holds across calls.
"""
import sectors

SECTORS = ["healthcare", "retail", "saas", "automotive", "hospitality", "financial_services"]
FULL = {"healthcare", "retail", "saas"}


def test_six_profiles_load():
    ids = sectors.list_sector_ids()
    assert set(ids) == set(SECTORS)
    assert sectors.default_sector() == "healthcare"


def test_list_sectors_has_band_and_depth():
    listed = sectors.list_sectors()
    assert len(listed) == 6
    for s in listed:
        assert s["band_label"] in ("below baseline", "baseline", "target", "stretch")
        assert s["depth"] in ("full", "stub")
    assert {s["sector"] for s in listed if s["depth"] == "full"} == FULL


def test_coerce_canonical_shape_for_every_sector():
    for sid in SECTORS:
        c = sectors.coerce(sid)
        assert c is not None
        # 5 universal cycle stages, sector-named.
        assert [s["id"] for s in c["stages"]] == sectors.UNIVERSAL_STAGES
        assert all(s["label"] for s in c["stages"])
        # Governance has all four sub-layers.
        for layer in ("rulesets", "protocols", "policies", "cadences"):
            assert layer in c["governance"]
        # Drill data present.
        assert c["cohorts"] and c["locations"]
        assert c["attribution"] == "A product of ArchLife"


def test_binding_constraint_is_weakest_stage():
    for sid in SECTORS:
        c = sectors.coerce(sid)
        constraint = next(s for s in c["stages"] if s["is_constraint"])
        assert constraint["ltv_cac"] == min(s["ltv_cac"] for s in c["stages"])
        assert c["headline"]["binding_constraint"] == constraint["id"]


def test_determinism():
    a = sectors.coerce("retail")
    b = sectors.coerce("retail")
    assert [s["ltv_cac"] for s in a["stages"]] == [s["ltv_cac"] for s in b["stages"]]


def test_endpoints(app_client):
    r = app_client.get("/api/sectors")
    assert r.status_code == 200
    assert len(r.json()["sectors"]) == 6
    assert r.json()["default"] == "healthcare"

    r2 = app_client.get("/api/sector/healthcare")
    assert r2.status_code == 200
    body = r2.json()
    assert body["labels"]["customer"] == "Patient"
    assert len(body["stages"]) == 5

    assert app_client.get("/api/sector/does-not-exist").status_code == 404


def test_meta_carries_attribution(app_client):
    m = app_client.get("/api/meta").json()
    assert m["attribution"] == "A product of ArchLife"
