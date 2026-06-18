"""Typed closure state machine (deepening #2; ADR-0004).

The substrate's accountability machine (repository.TRANSITIONS) is string-keyed
across the full intervention lifecycle. This is the *closure sub-path* as a
typed, server-enforced machine:

    proof_required -> closure_claimed -> closed_verified
                  \\-> escalated  (Q4 sector/company conflict, named-actor route)

It reuses the deepening-#1 CycleStage enum (a closure claim names the cycle
stage it pertains to) — the enums are defined once, in engine.opportunity_group.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict

from engine.opportunity_group import CycleStage  # reuse #1's enum — do NOT redefine


class ClosureState(str, Enum):
    PROOF_REQUIRED = "proof_required"
    CLOSURE_CLAIMED = "closure_claimed"
    CLOSED_VERIFIED = "closed_verified"
    ESCALATED = "escalated"


# Server-enforced transitions. closed_verified is terminal.
CLOSURE_TRANSITIONS = {
    ClosureState.PROOF_REQUIRED: {ClosureState.CLOSURE_CLAIMED, ClosureState.ESCALATED},
    ClosureState.CLOSURE_CLAIMED: {ClosureState.CLOSED_VERIFIED,
                                   ClosureState.PROOF_REQUIRED,  # verification rejected -> reopen
                                   ClosureState.ESCALATED},
    ClosureState.CLOSED_VERIFIED: set(),
    ClosureState.ESCALATED: {ClosureState.PROOF_REQUIRED},
}

# Map the substrate's string statuses onto the typed closure states.
FROM_SUBSTRATE = {
    "Proof Required": ClosureState.PROOF_REQUIRED,
    "Closure Claimed": ClosureState.CLOSURE_CLAIMED,
    "Closed": ClosureState.CLOSED_VERIFIED,
}


class InvalidTransition(Exception):
    """Raised when a closure transition is not permitted by the machine."""


def can_transition(src: ClosureState, dst: ClosureState) -> bool:
    return dst in CLOSURE_TRANSITIONS.get(src, set())


def validate_transition(src: ClosureState, dst: ClosureState) -> None:
    if not can_transition(src, dst):
        raise InvalidTransition(f"Illegal closure transition: {src.value} -> {dst.value}")


class ClosureClaim(BaseModel):
    """The structured claim a named actor submits to close an intervention."""

    model_config = ConfigDict(extra="forbid")

    stage: CycleStage                 # the cycle stage this closure pertains to (#1 enum)
    named_actor: str                  # who signs off (named-owner handoff)
    evidence_ids: list[str]
    consecutive_days: int = 0
    note: Optional[str] = None
