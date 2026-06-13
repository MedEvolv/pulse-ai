"""Intervention repository — the mutable-fabric seam (ADR-0002).

Owns the CP-05 closure state machine, sequence-based ID generation (ADR-0005),
per-session seeding, and persistence for interventions + closure proofs. Routes
depend on THIS interface, not on a storage client.

The in-memory adapter is the default and the one the public demo ships on
(ADR-0003). A Postgres adapter (`PgInterventionRepository`) implements the same
interface for real, `DATABASE_URL`-backed deployments; it is selected by
`build_repository()` when a Postgres URL is present.

Per ADR-0001 this backs only the mutable fabric — never the deterministic
catalogue, which `engine.py` owns.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

import engine

REQUIRED_CONSECUTIVE_DAYS = 5

# CP-05 accountability state machine (no direct closure). This is the fabric's
# domain rule, so it lives with the fabric — not in the HTTP layer.
TRANSITIONS = {
    "Detected": ["Reviewed", "Assigned", "Rejected"],
    "Reviewed": ["Assigned", "Rejected"],
    "Assigned": ["In Progress", "Reviewed", "Rejected"],
    "In Progress": ["Proof Required", "Rejected"],
    "Proof Required": ["Closure Claimed", "Rejected"],  # Closure Claimed only via claim_closure
    "Closure Claimed": ["Closed", "Reopened"],          # Closed only via verify
    "Closed": ["Reopened"],
    "Reopened": ["In Progress", "Assigned", "Rejected"],
    "Rejected": ["Reviewed"],
}
PATCH_BLOCKED = {"Closed", "Closure Claimed"}  # require dedicated claim/verify endpoints
ALL_STATUSES = list(TRANSITIONS.keys())


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def allowed_transitions(status: str) -> list[str]:
    """Transitions a caller may request directly (excludes claim/verify-only)."""
    return [s for s in TRANSITIONS.get(status, []) if s not in PATCH_BLOCKED]


# Seeded fabric for a fresh session: first 6 leakages, with a few pre-advanced
# so the demo opens on a realistic accountability queue.
_SEED_DEFAULTS = [
    ("OWNER-NEHA", "Assigned", "2026-06-17"),
    ("OWNER-VIKRAM", "In Progress", "2026-06-16"),
    (None, "Detected", None),
]


def _closure_criteria() -> str:
    return (f"Provide proof the metric crossed back over threshold for "
            f"{REQUIRED_CONSECUTIVE_DAYS} consecutive days.")


def _intervention_title(leakage: dict, override: Optional[str] = None) -> str:
    if override:
        return override
    base = f"Remediate {leakage['type'].replace('_', ' ')} in {leakage['region']}"
    return base + (f" / {leakage['clinic_code']}" if leakage.get("clinic_code") else "")


class InterventionRepository(ABC):
    """The seam. Both adapters satisfy this; routes never see storage details."""

    @abstractmethod
    async def seed_session(self, session_id: str) -> None: ...

    @abstractmethod
    async def list(self, session_id: str) -> list[dict]: ...

    @abstractmethod
    async def map_by_leakage(self, session_id: str) -> dict[str, dict]: ...

    @abstractmethod
    async def find(self, session_id: str, intervention_id: str) -> Optional[dict]: ...

    @abstractmethod
    async def find_by_leakage(self, session_id: str, leakage_id: str) -> Optional[dict]: ...

    @abstractmethod
    async def create(self, session_id: str, leakage: dict,
                     owner_id: Optional[str], due_date: Optional[str],
                     title: Optional[str]) -> dict: ...

    @abstractmethod
    async def save(self, session_id: str, intervention_id: str, changes: dict) -> None: ...

    @abstractmethod
    async def reset(self, session_id: str) -> None: ...

    @abstractmethod
    async def create_proof(self, session_id: str, proof: dict) -> dict: ...

    @abstractmethod
    async def find_proof(self, session_id: str, proof_id: str) -> Optional[dict]: ...

    @abstractmethod
    async def save_proof(self, session_id: str, proof_id: str, changes: dict) -> None: ...


class MemInterventionRepository(InterventionRepository):
    """In-memory adapter. Per-process, not durable — the demo's storage (ADR-0003).

    IDs are adapter-owned and monotonic per session (ADR-0005): a counter, never
    `count(rows)+1`, so deletes/reopens can't cause an ID to be reused.
    """

    def __init__(self):
        self._interventions: dict[str, list[dict]] = {}
        self._proofs: dict[str, list[dict]] = {}
        self._int_seq: dict[str, int] = {}
        self._proof_seq: dict[str, int] = {}

    def _next_int_id(self, session_id: str) -> str:
        n = self._int_seq.get(session_id, 0) + 1
        self._int_seq[session_id] = n
        return f"INT-{n:04d}"

    def _next_proof_id(self, session_id: str) -> str:
        n = self._proof_seq.get(session_id, 0) + 1
        self._proof_seq[session_id] = n
        return f"PROOF-{n:04d}"

    async def seed_session(self, session_id: str) -> None:
        if self._interventions.get(session_id):
            return
        rows: list[dict] = []
        for i, l in enumerate(engine.build_leakages()[:6]):
            owner, status, due = _SEED_DEFAULTS[i] if i < len(_SEED_DEFAULTS) else (None, "Detected", None)
            rows.append({
                "intervention_id": self._next_int_id(session_id),
                "session_id": session_id,
                "leakage_id": l["leakage_id"],
                "title": _intervention_title(l),
                "owner_id": owner,
                "status": status,
                "due_date": due,
                "closure_criteria": _closure_criteria(),
                "external_writeback": False,
                "proof_id": None,
                "notes": [],
                "history": [{"at": now_iso(), "event": "seeded", "status": status}],
            })
        self._interventions[session_id] = rows

    async def list(self, session_id: str) -> list[dict]:
        return [dict(d) for d in self._interventions.get(session_id, [])]

    async def map_by_leakage(self, session_id: str) -> dict[str, dict]:
        return {d["leakage_id"]: dict(d) for d in self._interventions.get(session_id, [])}

    async def find(self, session_id: str, intervention_id: str) -> Optional[dict]:
        for d in self._interventions.get(session_id, []):
            if d["intervention_id"] == intervention_id:
                return dict(d)
        return None

    async def find_by_leakage(self, session_id: str, leakage_id: str) -> Optional[dict]:
        for d in self._interventions.get(session_id, []):
            if d["leakage_id"] == leakage_id:
                return dict(d)
        return None

    async def create(self, session_id: str, leakage: dict,
                     owner_id: Optional[str], due_date: Optional[str],
                     title: Optional[str]) -> dict:
        doc = {
            "intervention_id": self._next_int_id(session_id),
            "session_id": session_id,
            "leakage_id": leakage["leakage_id"],
            "title": _intervention_title(leakage, title),
            "owner_id": owner_id,
            "status": "Assigned" if owner_id else "Detected",
            "due_date": due_date,
            "closure_criteria": _closure_criteria(),
            "external_writeback": False,
            "proof_id": None,
            "notes": [],
            "history": [{"at": now_iso(), "event": "created",
                         "status": "Assigned" if owner_id else "Detected"}],
        }
        self._interventions.setdefault(session_id, []).append(doc)
        return dict(doc)

    async def save(self, session_id: str, intervention_id: str, changes: dict) -> None:
        for d in self._interventions.get(session_id, []):
            if d["intervention_id"] == intervention_id:
                d.update(changes)
                return

    async def reset(self, session_id: str) -> None:
        self._interventions.pop(session_id, None)
        self._proofs.pop(session_id, None)
        self._int_seq.pop(session_id, None)
        self._proof_seq.pop(session_id, None)

    async def create_proof(self, session_id: str, proof: dict) -> dict:
        doc = dict(proof)
        doc["proof_id"] = self._next_proof_id(session_id)
        doc["session_id"] = session_id
        self._proofs.setdefault(session_id, []).append(doc)
        return dict(doc)

    async def find_proof(self, session_id: str, proof_id: str) -> Optional[dict]:
        for d in self._proofs.get(session_id, []):
            if d["proof_id"] == proof_id:
                return dict(d)
        return None

    async def save_proof(self, session_id: str, proof_id: str, changes: dict) -> None:
        for d in self._proofs.get(session_id, []):
            if d["proof_id"] == proof_id:
                d.update(changes)
                return


def build_repository() -> InterventionRepository:
    """Select the fabric adapter by environment (ADR-0003).

    `DATABASE_URL` present -> Postgres (real deployment); otherwise in-memory
    (the public demo). The Postgres adapter is added in a follow-up slice of
    issue #1 and verified against a real Postgres; until then a DATABASE_URL is
    an explicit, loud error rather than a silent in-memory fallback.
    """
    import os
    if os.environ.get("DATABASE_URL"):
        raise NotImplementedError(
            "PgInterventionRepository is not implemented yet (issue #1 follow-up). "
            "Unset DATABASE_URL to use the in-memory adapter, or implement the "
            "Postgres adapter and verify it against a real Postgres first."
        )
    return MemInterventionRepository()
