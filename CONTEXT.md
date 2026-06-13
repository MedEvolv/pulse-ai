# Pulse AI

The Revenue Operations intelligence layer for a dental-clinic network: it surfaces where
acquisition revenue leaks between lead and attended appointment, and drives evidence-backed
interventions to recover it.

This is the **glossary** — canonical terms and the words to avoid. Implementation lives in
code; revenue-domain terms (funnel stages, metrics, leakage taxonomy, opportunity groups)
are defined authoritatively in `docs/pulse-00-canonical-contract.md` and are not duplicated
here. This file captures terms resolved in grilling sessions that aren't already pinned there.

## Language

### Storage

**Deterministic catalogue**:
The read-only dataset `engine.py` generates from a fixed seed — leads, contact attempts,
appointments, revenue, reputation events, leakages, opportunity groups, and evidence. It is
identical on every run and is the single source of truth for those facts. It is *never*
persisted to the database.
_Avoid_: "the data", "seed data", "the dataset" (ambiguous with the mutable fabric).

**Mutable fabric**:
The user-created, changeable state that *does* persist: interventions, closure proofs, and
model-budget/cache. This is the only thing the database backs, and the only thing shared
with ReputationOS through the `core` schema. It is the alignment keystone.
_Avoid_: "the records", "the state" (say which: catalogue or fabric).

**Adapter**:
The storage implementation selected at runtime by environment — in-memory (default),
Mongo (`MONGO_URL`), or Postgres (`DATABASE_URL`). An adapter backs only the mutable
fabric; it never serves the deterministic catalogue.
_Avoid_: "the backend" (overloaded with the FastAPI service), "the store".

**Cited evidence**:
The subset of catalogue evidence that gets persisted into `core.evidence` — and only that
subset — because a closure proof references it. The rest of the catalogue's evidence is
never written to the database.
_Avoid_: "the evidence" (unqualified — most catalogue evidence is never persisted).
