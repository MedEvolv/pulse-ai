"""Fabric unit tests through the InterventionRepository interface (ADR-0002).

The point of the seam: the CP-05 closure machinery is now testable WITHOUT the
FastAPI app and WITHOUT any database — the interface is the test surface. These
run on the in-memory adapter with no external service.
"""
import asyncio

import repository
from repository import (
    MemInterventionRepository, allowed_transitions, PATCH_BLOCKED,
    REQUIRED_CONSECUTIVE_DAYS,
)


def run(coro):
    return asyncio.run(coro)


def test_seed_is_idempotent_and_sequential():
    repo = MemInterventionRepository()
    run(repo.seed_session("s1"))
    first = run(repo.list("s1"))
    run(repo.seed_session("s1"))  # second call must not duplicate
    second = run(repo.list("s1"))
    assert len(first) == len(second) == 6
    assert [i["intervention_id"] for i in second] == [f"INT-{n:04d}" for n in range(1, 7)]


def test_create_mints_sequential_ids_without_reuse():
    repo = MemInterventionRepository()
    run(repo.seed_session("s1"))
    leak = {"leakage_id": "LEAK-999", "type": "low_contact_rate", "region": "West"}
    a = run(repo.create("s1", leak, owner_id=None, due_date=None, title=None))
    b = run(repo.create("s1", {**leak, "leakage_id": "LEAK-998"}, None, None, None))
    # sequence continues past the 6 seeded — never count()+1 of live rows
    assert a["intervention_id"] == "INT-0007"
    assert b["intervention_id"] == "INT-0008"


def test_allowed_transitions_exclude_claim_and_verify_only():
    # Closure Claimed is reachable only via claim_closure, not a direct PATCH.
    assert "Closure Claimed" in PATCH_BLOCKED and "Closed" in PATCH_BLOCKED
    assert allowed_transitions("Proof Required") == ["Rejected"]
    assert allowed_transitions("Closure Claimed") == ["Reopened"]


def test_full_closure_lifecycle_through_the_seam():
    repo = MemInterventionRepository()
    run(repo.seed_session("s1"))
    iv = run(repo.list("s1"))[2]
    iid = iv["intervention_id"]

    # walk Detected -> ... -> Proof Required purely through the repo
    for status in ("Reviewed", "Assigned", "In Progress", "Proof Required"):
        run(repo.save("s1", iid, {"status": status}))
    assert run(repo.find("s1", iid))["status"] == "Proof Required"

    # claim closure: proof gets an adapter-owned id, intervention advances
    proof = run(repo.create_proof("s1", {
        "intervention_id": iid, "consecutive_days": REQUIRED_CONSECUTIVE_DAYS,
        "evidence_ids": ["EV-CALL-0001"], "verification": None,
    }))
    assert proof["proof_id"] == "PROOF-0001"
    run(repo.save("s1", iid, {"status": "Closure Claimed", "proof_id": proof["proof_id"]}))

    # verify -> Closed, and the proof carries the verification
    run(repo.save_proof("s1", proof["proof_id"], {"verification": {"decision": "approved"}}))
    run(repo.save("s1", iid, {"status": "Closed"}))

    assert run(repo.find("s1", iid))["status"] == "Closed"
    assert run(repo.find_proof("s1", proof["proof_id"]))["verification"]["decision"] == "approved"


def test_reset_clears_the_session():
    repo = MemInterventionRepository()
    run(repo.seed_session("s1"))
    run(repo.reset("s1"))
    assert run(repo.list("s1")) == []


def test_sessions_are_isolated():
    repo = MemInterventionRepository()
    run(repo.seed_session("a"))
    run(repo.seed_session("b"))
    iid = run(repo.list("a"))[0]["intervention_id"]
    run(repo.save("a", iid, {"status": "Reviewed"}))
    # same id in session b is untouched
    b_match = next(i for i in run(repo.list("b")) if i["intervention_id"] == iid)
    assert b_match["status"] != "Reviewed"


def test_database_url_without_pg_adapter_is_loud(monkeypatch):
    # ADR-0003: a DATABASE_URL must not silently fall back to in-memory.
    monkeypatch.setenv("DATABASE_URL", "postgresql://x/y")
    try:
        repository.build_repository()
        assert False, "expected NotImplementedError"
    except NotImplementedError:
        pass
