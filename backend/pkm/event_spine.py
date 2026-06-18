"""Append-only event spine — the interface (deepening #2; ADR-0003).

The closure event spine is append-only and is the source of truth for the
company PKM. The contract is deliberately tiny:

    append(event) -> event_id     # never mutates or deletes
    get(intervention_id) -> list[ClosureEvent]

Append-only is enforced by the adapters: there is no update() or delete().
Snapshot projections (the operator-queryable current state) are derived from
the spine, never the other way round.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from engine.closure_event import ClosureEvent


class EventSpine(ABC):
    """The append-only seam. Both adapters satisfy exactly this."""

    @abstractmethod
    def append(self, event: ClosureEvent) -> str:
        """Append an immutable event; return its spine event_id. Never mutates."""
        ...

    @abstractmethod
    def get(self, intervention_id: str) -> list[ClosureEvent]:
        """All closure events for an intervention, in append order."""
        ...

    @abstractmethod
    def all(self) -> list[ClosureEvent]:
        """The full spine, in append order (for snapshot projection)."""
        ...
