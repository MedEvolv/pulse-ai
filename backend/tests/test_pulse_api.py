"""Offline contract & engine tests for Pulse AI (CP-09.4).

No model calls (MODEL_ENABLED=false via conftest). No demo-DB mutation.
Covers the five foundational corrections: economic truth, AI validation,
honest evaluation, model budget defaults, proof-based closure.
"""
import engine
import briefing
import evaluation
from brief_validation import validate_brief_output


# ---------------------------------------------------------------------------
# CP-01 economic truth
# ---------------------------------------------------------------------------
def test_waterfall_telescopes_to_benchmark_delta():
    region = "REG-NORTH"
    m = engine.compute_metrics("current", region)
    b = engine.benchmark_rates()
    L, C, B, S = m["leads"], m["contact_rate"], m["booking_rate"], m["show_rate"]
    Cb, Bb, Sb = b["contact"]["value"], b["booking"]["value"], b["show"]["value"]
    delta = L * Cb * Bb * Sb - L * C * B * S
    groups = engine.region_opportunity_groups(region)
    raw_sum = sum(g["raw_additional_attended"] for g in groups)
    assert abs(raw_sum - delta) < 0.01


def test_unique_pools_are_the_only_additive_groups():
    summary = engine.regional_opportunity_summary("REG-NORTH")
    assert summary["unique_opportunity_pools"] == len(summary["opportunity_groups"])
    total = sum(g["display_additional_attended"] for g in summary["opportunity_groups"])
    assert summary["estimated_attendance_opportunity"] == total
    # every group is at a distinct stage
    stages = [g["stage"] for g in summary["opportunity_groups"]]
    assert len(stages) == len(set(stages))


def test_alerts_never_additive_and_share_groups():
    leaks = engine.leakages_for("REG-NORTH")
    for l in leaks:
        assert l["is_additive_in_summary"] is False
    # the two contact alerts share one opportunity group
    contact = [l for l in leaks if l["stage"] == "contact"]
    assert len({l["opportunity_group_id"] for l in contact}) == 1


def test_high_cost_is_diagnostic_with_no_pool():
    leaks = engine.leakages_for("REG-NORTH")
    hc = next(l for l in leaks if l["type"] == "high_cost_per_attended")
    assert hc["opportunity_relationship"] == "diagnostic"
    assert hc["opportunity_group_id"] is None
    assert hc["recoverable_value_inr"] == 0


def test_clinic_allocation_never_exceeds_regional_show_pool():
    region = "REG-NORTH"
    show = engine.opportunity_group_for(region, "show")
    alloc = engine.clinic_show_allocation(region)
    assert sum(a["display_additional_attended"] for a in alloc.values()) <= show["display_additional_attended"]


def test_north_has_at_least_three_high_severity():
    hi = [l for l in engine.leakages_for("REG-NORTH") if l["severity"] in ("Critical", "High")]
    assert len(hi) >= 3


def test_funnel_ends_at_attended():
    f = engine.funnel("current", "REG-NORTH")
    assert [s["stage_key"] for s in f] == ["captured", "contacted", "appointment_booked", "attended"]


# ---------------------------------------------------------------------------
# CP-06 metric evidence
# ---------------------------------------------------------------------------
def test_metric_evidence_is_cohort_faithful():
    mev = engine.build_metric_evidence()
    rec = mev["MEV-REG-NORTH-CONTACT-2026-06"]
    m = engine.compute_metrics("current", "REG-NORTH")
    assert rec["numerator"] == m["contacted"]
    assert rec["denominator"] == m["leads"]
    assert rec["cohort_hash"].startswith("sha256:")


# ---------------------------------------------------------------------------
# CP-02 strict validators
# ---------------------------------------------------------------------------
def _allow():
    facts = briefing.build_facts("REG-NORTH")
    amids, aeids = briefing.allowlists(facts)
    return sorted(amids)[0], sorted(aeids)[0], amids, aeids


def _valid(mid, eid, confidence="high"):
    return {
        "headline": "North loses efficiency after capture",
        "summary": "Contact lags the best comparable region, capping downstream attendance.",
        "top_findings": [{
            "finding": "Contact response lags the best comparable region.",
            "why_it_matters": "It caps downstream bookings and attendance.",
            "metric_ids": [mid], "evidence_ids": [eid], "confidence": confidence}],
        "recommended_interventions": [{
            "title": "Review telecalling response times.", "owner_role": "telecalling",
            "priority": "high", "evidence_ids": [eid], "human_approval_required": True}],
        "insufficient_evidence": False, "limitations": ["Synthetic data"]}


def test_validator_accepts_grounded_brief():
    mid, eid, amids, aeids = _allow()
    ok, reason, clean = validate_brief_output(_valid(mid, eid), amids, aeids, "high")
    assert ok and reason is None


def test_validator_rejects_invented_evidence():
    mid, eid, amids, aeids = _allow()
    b = _valid(mid, eid); b["top_findings"][0]["evidence_ids"] = ["EV-FAKE-1"]
    ok, reason, _ = validate_brief_output(b, amids, aeids, "high")
    assert not ok and reason == "MODEL_OUTPUT_PROVENANCE_FAILED"


def test_validator_rejects_empty_evidence():
    mid, eid, amids, aeids = _allow()
    b = _valid(mid, eid); b["top_findings"][0]["evidence_ids"] = []
    ok, reason, _ = validate_brief_output(b, amids, aeids, "high")
    assert not ok and reason == "MODEL_OUTPUT_PROVENANCE_FAILED"


def test_validator_rejects_ungrounded_number():
    mid, eid, amids, aeids = _allow()
    b = _valid(mid, eid); b["summary"] = "Contact rate fell to 12 percent."
    ok, reason, _ = validate_brief_output(b, amids, aeids, "high")
    assert not ok and reason == "MODEL_OUTPUT_NUMERIC_FAILED"


def test_validator_rejects_pii_email_mobile_aadhaar():
    mid, eid, amids, aeids = _allow()
    for pii in ["ping x@y.com", "call 98765 43210", "ref 1234 5678 9012"]:
        b = _valid(mid, eid); b["summary"] = pii
        ok, reason, _ = validate_brief_output(b, amids, aeids, "high")
        assert not ok and reason == "MODEL_OUTPUT_PRIVACY_FAILED"


def test_validator_rejects_confidence_escalation():
    mid, eid, amids, aeids = _allow()
    ok, reason, _ = validate_brief_output(_valid(mid, eid, "high"), amids, aeids, "low")
    assert not ok and reason == "MODEL_OUTPUT_PROVENANCE_FAILED"


def test_validator_rejects_extra_key_and_autonomous_action():
    mid, eid, amids, aeids = _allow()
    b = _valid(mid, eid); b["unexpected"] = 1
    ok, reason, _ = validate_brief_output(b, amids, aeids, "high")
    assert not ok and reason == "MODEL_OUTPUT_SCHEMA_FAILED"
    b2 = _valid(mid, eid); b2["recommended_interventions"][0]["human_approval_required"] = False
    ok2, reason2, _ = validate_brief_output(b2, amids, aeids, "high")
    assert not ok2 and reason2 == "MODEL_OUTPUT_SCHEMA_FAILED"


# ---------------------------------------------------------------------------
# CP-03 honest evaluation (offline, no hardcoded scores)
# ---------------------------------------------------------------------------
def test_evaluation_is_release_ready_and_offline():
    r = evaluation.run_fixtures()
    assert r["name"] == "Offline Evaluation Score"
    assert r["modes"]["optional_model_contract_tests"]["executed"] is False
    assert r["scenario_count"] >= 10
    assert r["dimensions"]["privacy_safety"] == 100
    assert r["dimensions"]["provenance_validity"] == 100
    assert r["release_ready"] is True


# ---------------------------------------------------------------------------
# CP-04 model budget defaults (no model in tests)
# ---------------------------------------------------------------------------
def test_model_disabled_in_tests():
    import model_budget
    assert model_budget.config()["enabled"] is False


def test_brief_endpoint_default_is_deterministic(app_client):
    r = app_client.post("/api/brief", json={"region": "REG-NORTH"})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] in ("deterministic", "deterministic_fallback")
    assert body["cache_status"] == "deterministic"


def test_brief_use_model_disabled_falls_back(app_client):
    r = app_client.post("/api/brief", json={"region": "REG-NORTH", "use_model": True})
    body = r.json()
    assert body["mode"] == "deterministic_fallback"
    assert body["reason_code"] == "MODEL_DISABLED"


def test_unsupported_question_is_bounded(app_client):
    r = app_client.post("/api/brief", json={"region": "REG-NORTH",
                                            "question": "Draft a five year acquisition plan."})
    body = r.json()
    assert body["insufficient_evidence"] is True
    assert body["mode"] == "bounded"


# ---------------------------------------------------------------------------
# CP-07 validation + session isolation
# ---------------------------------------------------------------------------
def test_bad_region_is_422(app_client):
    assert app_client.get("/api/cockpit", params={"region": "REG-FAKE"}).status_code == 422


def test_drilldown_cohort_filters(app_client):
    r = app_client.get("/api/journeys", params={"region": "REG-NORTH", "funnel_stage": "contacted"})
    body = r.json()
    assert body["applied_filters"]["funnel_stage"] == "contacted"
    assert all(row["connected"] is False for row in body["journeys"])


# ---------------------------------------------------------------------------
# CP-05 proof-based closure state machine
# ---------------------------------------------------------------------------
def test_proof_based_closure_workflow(app_client, session_header):
    iv = app_client.get("/api/interventions", headers=session_header).json()["interventions"][2]
    iid = iv["intervention_id"]

    # direct close is forbidden
    assert app_client.patch(f"/api/interventions/{iid}",
                            json={"status": "Closed"}, headers=session_header).status_code == 409

    for st in ["Assigned", "In Progress", "Proof Required"]:
        r = app_client.patch(f"/api/interventions/{iid}",
                             json={"status": st, "owner_id": "OWNER-NEHA"}, headers=session_header)
        assert r.status_code == 200, r.text

    # insufficient proof rejected
    bad = app_client.post(f"/api/interventions/{iid}/proof",
                          json={"consecutive_days": 2, "evidence_ids": ["MEV-REG-NORTH-CONTACT-2026-06"]},
                          headers=session_header)
    assert bad.status_code == 422

    # valid claim -> Closure Claimed
    claim = app_client.post(f"/api/interventions/{iid}/proof",
                            json={"consecutive_days": 5, "evidence_ids": ["MEV-REG-NORTH-CONTACT-2026-06"]},
                            headers=session_header)
    assert claim.status_code == 200
    assert claim.json()["intervention"]["status"] == "Closure Claimed"

    # separate verification -> Closed
    ver = app_client.post(f"/api/interventions/{iid}/verify",
                          json={"decision": "approved"}, headers=session_header)
    assert ver.json()["status"] == "Closed"


def test_session_isolation(app_client):
    h1 = {"X-Demo-Session-ID": "iso-aaa"}
    h2 = {"X-Demo-Session-ID": "iso-bbb"}
    iv = app_client.get("/api/interventions", headers=h1).json()["interventions"][0]
    iid = iv["intervention_id"]
    app_client.patch(f"/api/interventions/{iid}", json={"status": "Reviewed"}, headers=h1)
    other = app_client.get("/api/interventions", headers=h2).json()["interventions"]
    target = next(i for i in other if i["intervention_id"] == iid)
    assert target["status"] in ("Detected", "Assigned", "In Progress")  # unaffected by session 1
