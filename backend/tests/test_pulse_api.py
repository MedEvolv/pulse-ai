"""Pulse AI backend API tests."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback: read frontend env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---- Health & meta ----
class TestHealth:
    def test_health(self, api):
        r = api.get(f"{BASE_URL}/api/health", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["status"] == "ok"
        assert "data_version" in d
        assert "rule_version" in d

    def test_meta(self, api):
        r = api.get(f"{BASE_URL}/api/meta", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert len(d["regions"]) >= 3
        assert any(rg["region_id"] == "REG-NORTH" for rg in d["regions"])


# ---- Cockpit ----
class TestCockpit:
    def test_north_default(self, api):
        r = api.get(f"{BASE_URL}/api/cockpit?region=REG-NORTH", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["region"] == "REG-NORTH"
        assert len(d["health_strip"]) == 5
        keys = [t["key"] for t in d["health_strip"]]
        assert keys == ["spend_inr", "leads", "contact_rate", "show_rate", "cost_per_attended_inr"]
        assert d["funnel"] and len(d["funnel"]) >= 4
        # North should be at-risk
        north = next(c for c in d["comparison"] if c["region_id"] == "REG-NORTH")
        assert north["at_risk"] is True
        assert north["high_severity_leakages"] >= 2

    def test_west_healthy(self, api):
        r = api.get(f"{BASE_URL}/api/cockpit?region=REG-WEST", timeout=15)
        assert r.status_code == 200
        d = r.json()
        west = next(c for c in d["comparison"] if c["region_id"] == "REG-WEST")
        assert west["at_risk"] is False

    def test_south(self, api):
        r = api.get(f"{BASE_URL}/api/cockpit?region=REG-SOUTH", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["region"] == "REG-SOUTH"


# ---- Leakages ----
class TestLeakages:
    def test_north_three_high(self, api):
        r = api.get(f"{BASE_URL}/api/leakages?region=REG-NORTH", timeout=15)
        assert r.status_code == 200
        leaks = r.json()["leakages"]
        high = [l for l in leaks if l["severity"] in ("High", "Critical")]
        assert len(high) >= 3, f"Expected >=3 high severity in North, got {len(high)}"

    def test_leakage_detail(self, api):
        leaks = api.get(f"{BASE_URL}/api/leakages?region=REG-NORTH", timeout=15).json()["leakages"]
        lid = leaks[0]["leakage_id"]
        r = api.get(f"{BASE_URL}/api/leakages/{lid}", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["leakage"]["leakage_id"] == lid
        assert "evidence" in d

    def test_leakage_not_found(self, api):
        r = api.get(f"{BASE_URL}/api/leakages/NOPE-9999", timeout=15)
        assert r.status_code == 404


# ---- Interventions (CRUD with persistence) ----
class TestInterventions:
    def test_list_seeded(self, api):
        r = api.get(f"{BASE_URL}/api/interventions", timeout=15)
        assert r.status_code == 200
        items = r.json()["interventions"]
        assert len(items) >= 1
        for it in items:
            assert it.get("external_writeback") is False

    def test_assign_update_persistence(self, api):
        items = api.get(f"{BASE_URL}/api/interventions", timeout=15).json()["interventions"]
        # find one in New state (or any)
        target = next((i for i in items if i["status"] == "New"), items[0])
        iid = target["intervention_id"]
        # Update: assign owner
        r = api.patch(f"{BASE_URL}/api/interventions/{iid}",
                      json={"owner_id": "OWNER-NEHA", "status": "Assigned",
                            "due_date": "2026-12-31", "note": "TEST_assigned"}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["owner_id"] == "OWNER-NEHA"
        assert d["status"] == "Assigned"
        assert d["due_date"] == "2026-12-31"
        # persistence
        r2 = api.get(f"{BASE_URL}/api/interventions", timeout=15)
        match = next(i for i in r2.json()["interventions"] if i["intervention_id"] == iid)
        assert match["status"] == "Assigned"
        assert any(n.get("text") == "TEST_assigned" for n in match.get("notes", []))

    def test_status_transitions(self, api):
        items = api.get(f"{BASE_URL}/api/interventions", timeout=15).json()["interventions"]
        iid = items[0]["intervention_id"]
        for st in ["Reviewed", "In Progress", "Proof Required", "Closed"]:
            r = api.patch(f"{BASE_URL}/api/interventions/{iid}",
                          json={"status": st}, timeout=15)
            assert r.status_code == 200, f"{st} -> {r.text}"
            assert r.json()["status"] == st

    def test_invalid_status(self, api):
        items = api.get(f"{BASE_URL}/api/interventions", timeout=15).json()["interventions"]
        iid = items[0]["intervention_id"]
        r = api.patch(f"{BASE_URL}/api/interventions/{iid}",
                      json={"status": "Bogus"}, timeout=15)
        assert r.status_code == 400


# ---- Brief ----
class TestBrief:
    def test_deterministic_brief(self, api):
        r = api.post(f"{BASE_URL}/api/brief",
                     json={"region": "REG-NORTH",
                           "question": "Why is North Region underperforming?",
                           "use_model": False}, timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert "headline" in d
        assert d.get("mode") in ("deterministic", "bounded", "model")
        assert "evidence_pool" in d

    def test_model_brief(self, api):
        t0 = time.time()
        r = api.post(f"{BASE_URL}/api/brief",
                     json={"region": "REG-NORTH",
                           "question": "Why is North Region underperforming?",
                           "use_model": True}, timeout=90)
        elapsed = time.time() - t0
        assert r.status_code == 200, f"brief failed: {r.text}"
        d = r.json()
        assert d.get("mode") in ("model", "deterministic", "bounded")
        print(f"Brief mode={d.get('mode')} in {elapsed:.1f}s")


# ---- Journeys ----
class TestJourneys:
    def test_journeys_list(self, api):
        r = api.get(f"{BASE_URL}/api/journeys?region=REG-NORTH&limit=50", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["total"] >= 1
        # privacy: no PII
        for row in d["journeys"][:5]:
            for k in ("name", "email", "phone", "patient_name"):
                assert k not in row

    def test_journey_detail(self, api):
        d = api.get(f"{BASE_URL}/api/journeys?region=REG-NORTH&limit=5", timeout=15).json()
        lead_id = d["journeys"][0]["lead_id"]
        r = api.get(f"{BASE_URL}/api/journeys/{lead_id}", timeout=15)
        assert r.status_code == 200
        det = r.json()
        assert "timeline" in det and len(det["timeline"]) >= 1
        for ev in det["timeline"]:
            assert "source_system" in ev


# ---- Simulation ----
class TestSimulation:
    def test_sim_outputs(self, api):
        r = api.post(f"{BASE_URL}/api/simulation",
                     json={"region": "REG-NORTH",
                           "contact_improve_pp": 5,
                           "booking_improve_pp": 5,
                           "show_improve_pp": 5,
                           "avg_realized_value": 25000}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "baseline" in d and "simulated" in d
        assert d["simulated"]["additional_attended"] >= 0
        assert d["simulated"]["estimated_recoverable_value_inr"] >= 0

    def test_sim_reset(self, api):
        r = api.post(f"{BASE_URL}/api/simulation",
                     json={"region": "REG-NORTH"}, timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d["simulated"]["additional_attended"] == 0


# ---- Data Quality ----
class TestDataQuality:
    def test_sources(self, api):
        r = api.get(f"{BASE_URL}/api/data-quality", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert len(d["sources"]) == 6
        assert "identity_match_rate" in d
        assert isinstance(d["briefing_ready"], bool)


# ---- Evaluation ----
class TestEvaluation:
    def test_evaluation_full_score(self, api):
        r = api.get(f"{BASE_URL}/api/evaluation", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d.get("passed") == 10
        assert d.get("failed") == 0
        assert d.get("overall_score") == 100
