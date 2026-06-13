# Mutable fabric uses a relational repository, not a Mongo-emulation shim

## Context

The mutable fabric (ADR-0001) is accessed today through a Mongo-style interface:
`db.interventions.update_one({...}, {"$set": ...})`, `insert_one`, `find`, `$inc`/`upsert`,
`delete_many`. The `_MemDB` shim mimics Mongo. A Postgres adapter could either re-implement
that shim over JSONB blobs (drop-in, zero call-site changes) or expose a typed repository
backed by the relational columns in `docs/unified-database/schema.sql`.

## Decision

Introduce a typed **repository interface** (e.g. `create_intervention`,
`list_interventions(session)`, `claim_proof`, `verify`) that both the in-memory and Postgres
adapters implement. Interventions and closure proofs are stored as real relational rows in
the `core` schema — not as JSONB blobs. The ~18 Mongo-style call sites in `server.py` are
rewritten to use the repository.

## Why

The reason for choosing Postgres at all is the relational schema's payoff: the
`core.intervention.subject_type` check, foreign keys to `core.clinic` / `core.actor`,
Row-Level Security so each product mutates only its own subjects, and the
`core.intervention_feed` cross-product view. A Mongo-emulation-over-JSONB adapter runs but
discards every one of these — it would be a Postgres-shaped key-value store with none of the
alignment the schema was built for. The relational repository is what makes the fabric
genuinely shared with ReputationOS.

## Consequences

- Bounded refactor: ~18 call sites in one module, no behaviour change, covered by existing
  tests.
- Lets us replace the concurrency-unsafe count-based IDs (`AGENT.md` §24 risk 11) with
  generated IDs as part of the same change.
