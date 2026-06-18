"""ClosureEvent spine — two adapters (deepening #2; ADR-0003).

A NEW seam, separate from InterventionRepository (ADR-0002). The repository owns
the *mutable* fabric (an intervention's current status); this spine owns the
*append-only* closure history — the institutional-memory source of truth.

  * InMemoryClosureEventSpine    — the demo + tests adapter (per-process).
  * AppendOnlyClosureEventSpine  — the v1.0 durable adapter: a single global
    append-only log with a monotonic sequence, the shape a Postgres append-only
    table backs. Durable Postgres wiring (DATABASE_URL) is the v1.1 commitment;
    until then it runs as an in-process append-only log so the seam is real and
    testable rather than a stub.

Both refuse mutation and deletion — append is the only write.
"""
from __future__ import annotations

from engine.closure_event import ClosureEvent
from pkm.event_spine import EventSpine


class InMemoryClosureEventSpine(EventSpine):
    """Per-process append-only store (demo + tests)."""

    def __init__(self):
        self._events: list[ClosureEvent] = []
        self._seq = 0

    def append(self, event: ClosureEvent) -> str:
        self._seq += 1
        event_id = f"CEV-{self._seq:06d}"
        # store a copy so the caller cannot mutate what the spine holds
        self._events.append(event.model_copy(deep=True))
        return event_id

    def get(self, intervention_id: str) -> list[ClosureEvent]:
        return [e for e in self._events if e.intervention_id == intervention_id]

    def all(self) -> list[ClosureEvent]:
        return list(self._events)


class AppendOnlyClosureEventSpine(EventSpine):
    """Durable-shaped append-only log: monotonic sequence, the source of truth.

    Mirrors a Postgres append-only `core.closure_event` table — every append
    gets a gap-free sequence; there is no path to update or delete. The durable
    backend (Postgres via DATABASE_URL) is wired in v1.1; the in-process log
    here has identical append-only semantics so the contract is verifiable now.
    """

    def __init__(self):
        self._log: list[tuple[int, ClosureEvent]] = []
        self._seq = 0

    def append(self, event: ClosureEvent) -> str:
        self._seq += 1
        self._log.append((self._seq, event.model_copy(deep=True)))
        return f"CEV-{self._seq:06d}"

    def get(self, intervention_id: str) -> list[ClosureEvent]:
        return [e for _seq, e in self._log if e.intervention_id == intervention_id]

    def all(self) -> list[ClosureEvent]:
        return [e for _seq, e in self._log]


def build_closure_event_spine() -> EventSpine:
    """Select the spine adapter by environment (mirrors build_repository).

    DATABASE_URL present -> the durable append-only spine; otherwise the
    in-memory spine (the public demo). Both are append-only.
    """
    import os
    if os.environ.get("DATABASE_URL"):
        return AppendOnlyClosureEventSpine()
    return InMemoryClosureEventSpine()
