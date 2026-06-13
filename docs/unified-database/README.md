# Unified Database — ReputationOS + Pulse AI

**Status:** plan v0.1 · 2026-06-13
**Goal:** one shared, accessible database both products read and write, so ReputationOS and Pulse AI stay aligned on the same clinics, owners, evidence, events, and interventions instead of drifting on separate synthetic stores.

This folder is the source of truth for the schema. The strategic write-up lives in the vault at
`01_Projects/ReputationOps_Mirror/architecture--unified-database-reputationos-pulse-ai-2026-06-13.md`.

---

## 1. Why these two share a database

Per `decision--pulse-ai-product-convergence-v0.1`:

- **Pulse AI** is the Revenue Operations umbrella (lead → attended-appointment leakage).
- **ReputationOS** is a separately sellable complaint/NPS/SLA module **and** the reusable
  **intervention · ownership · evidence · closure** fabric underneath Pulse AI.

They are structural twins. Both already carry the same provenance fields today:
source system, source record id, ingest batch, event timestamp + observed-at, clinic/region/owner,
evidence references, confidence, and human-approval state. The only thing keeping them apart is that
each runs its own in-memory synthetic store. Putting that shared fabric in one `core` schema is the
alignment.

## 2. Chosen technology — Supabase Postgres (one project)

Recommendation, with the reasons it wins for *this* estate:

- **Relational integrity is the whole point.** Interventions reference leakages *and* tickets;
  evidence is cited by both products; clinics/owners must be the same rows. That is foreign-key
  work — Postgres, not Mongo. (Pulse's current optional Mongo / in-memory path stays only as a
  legacy/offline fallback.)
- **Accessible from both stacks.** ReputationOS (Next.js/TypeScript) via Prisma or `supabase-js`;
  Pulse AI (FastAPI/Python) via `asyncpg`/SQLAlchemy or `supabase-py`. One connection string each.
- **Already in the estate.** The Supabase MCP and Prisma MCP are connected, and the Dental Lab app
  already runs PostgreSQL/Prisma — so tooling, migration habits, and a hosting account exist.
- **Serverless-friendly.** Supabase ships a connection **pooler** (PgBouncer, transaction mode) —
  required because Pulse AI's backend runs as Vercel serverless functions that must not hold direct
  Postgres connections.

### Schema layout

| Schema | Owns | Read by |
|---|---|---|
| `core` | regions, clinics + alias crosswalk, actors, ingest batches, **evidence**, **event spine**, **interventions**, closure proofs | both |
| `pulse` | campaigns, leads, contact_attempts, appointments, revenue, leakages | Pulse AI (rw), analytics (ro) |
| `reputationos` | tickets, sla_policies, ticket events | ReputationOS (rw), analytics (ro) |

`core.intervention` carries a `subject_type` of `pulse_leakage` or `reputationos_ticket` — that single
table is the alignment keystone. Its status set matches the ReputationOS CP-05 accountability state
machine (no direct close; proof + verify), so both products share one closure lifecycle.
`core.intervention_feed` is one cross-product accountability queue.

## 3. The hard part — identity reconciliation

Pulse demo clinic codes (`DL-RHN-02`) and ReputationOS Clove/SAP codes describe the **same real
clinics** with different ids. Unification is only real once they resolve to one `core.clinic` row.

- `core.clinic` = canonical clinic (UID + agreed `canonical_code`).
- `core.clinic_alias (product, external_code) -> clinic_uid` = the crosswalk.
- Seed the crosswalk from the **Clove Master Tracker + KML join** (576 clinics, already reconciled in
  `reputationos/.../private-clinic-locations`) and the Pulse demo catalogue.
- Do the same for `core.actor` (owners/agents/clinic-heads) and `core.region`
  (Pulse's coarse bands ↔ ReputationOS's region/sub_region/zone).

Until the crosswalk exists, the two products cannot truthfully claim to share data. Build it first.

## 4. Access & safety model

- Roles: `pulse_app`, `reputationos_app` (each rw on its own domain + scoped rw on its own
  intervention subjects), `analytics_ro` (read-only everywhere).
- **Row Level Security** on `core.intervention` and `core.evidence` so a product can only mutate its
  own subjects.
- MVP privacy rules from the convergence decision still hold: pseudonymous person ids only, no clinical
  notes, no raw name/phone/email in the intelligence layer, `external_writeback = false`.
- Secrets via each app's env (`DATABASE_URL` pooled / `DIRECT_URL` for migrations); never committed.

## 5. Migration sequence

1. Create the Supabase project (or adopt the Dental Lab project as host — **open decision**, §7).
2. Apply `schema.sql` as the first migration (`core` → `pulse` → `reputationos`).
3. Apply the access/RLS migration (roles, grants, policies).
4. **Seed the crosswalk** (`core.region`, `core.clinic`, `core.clinic_alias`, `core.actor`).
5. Port existing deterministic synthetic data into `pulse.*` and `reputationos.*` via seed scripts so
   demos render identically to today (Pulse `engine.py` generator → rows; ReputationOS `demo-data` → rows).
6. **Pulse AI**: add a `DATABASE_URL` (Postgres) repository layer behind the existing route handlers.
   The backend already abstracts storage (`_MemDB`); add a `PgDB` alongside it, selected by env. No
   route signatures change.
7. **ReputationOS**: introduce Prisma (or `supabase-js`) reading `core` + `reputationos`, replacing the
   in-memory store behind the existing selectors.
8. Cut over one product at a time; keep the in-memory path as offline/test fallback.

Nothing here enables paid cloud services, sends real patient data to a model, or writes back to any
external system. Those remain gated.

## 6. Where the adapter slots into Pulse AI

- `backend/server.py` already abstracts storage (`_MemDB` today; Mongo when `MONGO_URL` is set). The
  Postgres adapter is a third option behind the same async interface, selected by env.
- A future `backend/db/pg.py` implements that interface against Postgres (asyncpg/SQLAlchemy). No route
  signatures change.

## 7. Decisions (approved 2026-06-13)

1. **Host → new dedicated Supabase project** (not the Dental Lab project). Dental Lab is heading into
   a friendly-lab pilot; a separate project keeps uptime, migrations, and billing isolated, and a new
   project is free.
2. **ReputationOS → Prisma as a typed client in introspection mode (`prisma db pull`); schema
   migrations owned by SQL/Supabase, not Prisma Migrate.** A shared, multi-schema, two-language DB
   needs one migration authority (this `schema.sql` / Supabase migrations). Prisma gives ReputationOS
   a typed reader/writer without an ORM-vs-SQL migration tug-of-war; Pulse uses generated Python types.
3. **Canonical clinic → yes.** Identity is keyed by internal `clinic_uid`; `canonical_code` = Clove/SAP
   (real, 576 clinics); Pulse demo codes alias onto it. Raw SAP codes are an internal join key only and
   must never be rendered on demo/external surfaces (honors the existing Clove privacy boundary).
4. **Environments → one dedicated project now; add a separate prod project when real data arrives.**
   All data is currently synthetic, so standing up prod now is premature and risks free-tier project
   limits. The promotion trigger is concrete: the first real export/pilot dataset (also the DPDP /
   data-residency trigger).

No agent may provision this database merely because the schema exists. The hard prerequisites stay:
**Pulse-00** (canonical journey, metric definitions, leakage taxonomy, export contract) and the
clinic/actor/region **identity crosswalk**, both of which can be built now without provisioning anything.
