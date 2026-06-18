"""Tests for the operator query + RAG dispatch seam (deepening #5; ADR-0003/0004).

Covers the typed OperatorQuery library (~30/sector, 6 sectors), the lookup
surface, the 3-adapter dispatch (Qdrant retrieve -> engine compute -> AINarrative),
the <=5 Qdrant cap, the 3 knowledge layers, real-ref grounding, and the
POST /api/operator_query route (pre-canned only).
"""
import pytest

from engine.operator_query import OperatorQuery
from engine.pre_canned_library import build_library
from pkm import operator_query_library as lib
from pkm import query_dispatch
from pkm.closure_event_spine import InMemoryClosureEventSpine
from engine.closure_event import ClosureEvent

SECTORS = ["healthcare", "retail", "saas", "automotive", "hospitality", "financial_services"]
NOW = "2026-06-19T10:00:00Z"


def test_library_is_typed_and_30_per_sector():
    L = build_library()
    assert all(isinstance(q, OperatorQuery) for q in L)
    for s in SECTORS:
        qs = lib.questions_for_sector(s)
        assert len(qs) == 30                       # ~30/sector (6 per stage x 5 stages)
        assert {q.answer_type for q in qs} == {
            "ltv_cac", "binding_constraint", "critical_few", "closure_history", "narrative"}
        assert len(lib.questions_for_stage(s, "retention")) == 6


def test_get_question_and_pre_canned_flag():
    q = lib.get_question("OQ-healthcare-retention-1")
    assert q is not None and q.pre_canned is True
    assert q.sector == "healthcare" and q.stage == "retention"
    assert lib.get_question("OQ-not-real") is None


def test_dispatch_cites_real_refs_and_three_layers():
    spine = InMemoryClosureEventSpine()
    q = lib.get_question("OQ-healthcare-retention-1")
    res = query_dispatch.dispatch(q, "REG-NORTH", spine, NOW)
    assert res["adapters"] == ["qdrant_closure_retriever", "engine_computation", "ai_narrative"]
    # real OpportunityGroup ref in provenance
    assert res["provenance"]["engine_computation"]["opportunity_group_ref"]
    # 3 knowledge layers
    assert [k["layer"] for k in res["knowledge_layers"]] == ["sector", "company", "customer"]


def test_closure_history_retrieval_capped_at_5():
    spine = InMemoryClosureEventSpine()
    # seed 7 closure events on the same opportunity group
    res0 = query_dispatch.dispatch(lib.get_question("OQ-healthcare-retention-1"), "REG-NORTH", spine, NOW)
    opp = res0["opportunity_group_ref"]
    for i in range(7):
        spine.append(ClosureEvent(closure_id=f"CL-{i}", intervention_id=f"INT-{i}",
                                  opportunity_group_ref=opp, claim={}, timestamp=NOW))
    q = lib.get_question("OQ-healthcare-retention-4")   # closure_history domain
    res = query_dispatch.dispatch(q, "REG-NORTH", spine, NOW)
    assert q.answer_type == "closure_history"
    assert res["answer"]["count"] <= 5                  # Qdrant cap
    assert len(res["retrieved_closure_event_ids"]) <= 5


def test_answer_type_routing():
    spine = InMemoryClosureEventSpine()
    kinds = {}
    for i in range(1, 7):
        q = lib.get_question(f"OQ-retail-spend-{i}")
        kinds[q.answer_type] = query_dispatch.dispatch(q, "REG-NORTH", spine, NOW)["answer"]
    assert "band" in kinds["ltv_cac"]
    assert kinds["binding_constraint"]["constraint_stage"]
    assert "coverage_share" in kinds["critical_few"]


# --- API route ---
def test_api_operator_query_library(app_client):
    body = app_client.get("/api/operator_query/library", params={"sector": "healthcare"}).json()
    assert body["count"] == 30


def test_api_operator_query_precanned_only(app_client, session_header):
    qid = "OQ-healthcare-retention-1"
    r = app_client.post("/api/operator_query", json={"query_id": qid, "region": "REG-NORTH"},
                        headers=session_header)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["query"]["query_id"] == qid
    assert body["provenance"]["engine_computation"]["opportunity_group_ref"]
    # free-text / unknown id rejected
    assert app_client.post("/api/operator_query",
                           json={"query_id": "tell me everything", "region": "REG-NORTH"},
                           headers=session_header).status_code == 404
