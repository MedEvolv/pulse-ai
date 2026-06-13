# Fabric IDs are adapter-owned and sequence-based

## Context

Intervention and proof IDs are currently computed in the route as `count_documents()+1`,
which is not concurrency-safe under a shared multi-writer database (`AGENT.md` §24 risk 11).
ADR-0002 commits to replacing them.

## Decision

ID generation moves into the adapter and is returned on insert — never computed in the route.
The Postgres adapter uses a database sequence with a readable prefix
(`'INT-' || lpad(nextval(...), 6, '0')` → `INT-000123`; likewise `PROOF-000123`); the
in-memory adapter keeps an internal counter. No ULIDs/UUIDs for fabric IDs.

## Why

The readable, monotonic form matches what the demo and `AGENT.md` already show and reads well
in the human accountability queue, while a sequence is fully concurrency-safe. ULIDs would
add distributed/offline minting strength the low-write, single-DB fabric doesn't need, at the
cost of opaque IDs in a triage list.
