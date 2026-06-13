# Cited evidence is lazily upserted into core.evidence at proof time

## Context

A closure proof requires at least one supporting evidence ID (`server.py` rejects an empty
list). Those IDs reference catalogue evidence (`EV-CALL-…`, `MEV-…`) produced by
`engine.get_evidence_index()`. Under ADR-0001 the deterministic catalogue — including its
evidence — is not persisted, yet `core.closure_proof_evidence` carries a foreign key to
`core.evidence`. An empty `core.evidence` cannot satisfy that FK.

## Decision

When a proof cites evidence IDs, resolve each ID against `engine.get_evidence_index()` and
**upsert just those rows** into `core.evidence`, then link them via
`core.closure_proof_evidence`. Only evidence that actually backs a real closure is persisted.

## Why

The closure proof is the one place evidence becomes load-bearing — a claim is only as strong
as its evidence. Persisting exactly the cited evidence keeps the FK honest and makes
`core.evidence` meaningful: it holds precisely the evidence behind real interventions across
both products, which is the shared-fabric value. It stays within ADR-0001 — we bulk-persist
nothing; we persist only the few rows that ground a mutable-fabric action.

## Consequences

A small resolve-and-upsert step runs at proof time (negligible — proofs are low-frequency,
human-driven). Evidence never cited by any proof never enters the database.
