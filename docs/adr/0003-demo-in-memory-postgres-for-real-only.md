# The public demo stays in-memory; Postgres backs real deployments only

## Context

Demo interventions are isolated per anonymous visitor via an `X-Demo-Session-ID`. The shared
`core.intervention` schema has no `session_id` column and its Row-Level Security isolates by
*product* (`pulse_app` / `reputationos_app`), not by anonymous visitor. So we must decide
whether anonymous demo writes ever reach the shared database.

## Decision

The adapter is chosen by environment-variable presence: `DATABASE_URL` set → Postgres (a
real, authenticated tenant); `MONGO_URL` set → Mongo; neither → in-memory. The public Vercel
demo sets none, so anonymous demo writes never touch the shared `core`. The `session_id`
isolation mechanism stays a demo-only concern inside the in-memory adapter; `core` gets no
anonymous-visitor column.

## Why

Real data is the trigger for Postgres (consistent with ADR-0001). Keeping anonymous,
ephemeral demo data out of `core` is both a privacy win and a cleanliness win — no stranger
rows pollute the cross-product accountability queue. The selection rule stays trivial, and a
demo reload giving each visitor a clean slate is acceptable (arguably better) for a
90-second walkthrough.

## Consequences

The demo cannot show interventions persisting across reloads or syncing live with
ReputationOS; that capability appears only in a real, `DATABASE_URL`-backed deployment.
