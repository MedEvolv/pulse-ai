-- =============================================================================
-- Unified Database Schema — ReputationOS + Pulse AI
-- Target: PostgreSQL 15+ (Supabase-managed)
-- Version: v0.1  (2026-06-13)
--
-- Design principle (from decision--pulse-ai-product-convergence-v0.1):
--   Pulse AI is the RevOps umbrella. ReputationOS is a sellable module AND the
--   reusable intervention / ownership / evidence / closure fabric underneath.
--   => Shared "fabric" lives in schema `core`. Each product keeps its own
--      domain schema (`pulse`, `reputationos`) but reuses core dimensions,
--      evidence, events, and interventions. Alignment is achieved by both
--      products pointing at the SAME core tables, not by copying data.
--
-- Append-only spine: `core.event` is the source of truth. Domain tables
-- (pulse.lead, reputationos.ticket, ...) are current-state projections that
-- can be rebuilt from events. Every derived claim keeps its provenance.
-- =============================================================================

create schema if not exists core;
create schema if not exists pulse;
create schema if not exists reputationos;

-- -----------------------------------------------------------------------------
-- CORE: shared dimensions
-- -----------------------------------------------------------------------------

-- Regions form a hierarchy (region -> sub_region -> zone). Pulse uses coarse
-- REG-NORTH/WEST/SOUTH; ReputationOS uses finer region/sub_region/zone. The
-- hierarchy holds both: Pulse reads at the top band, ReputationOS at the leaf.
create table core.region (
  region_uid    uuid primary key default gen_random_uuid(),
  code          text unique not null,          -- canonical, e.g. 'REG-NORTH'
  name          text not null,
  parent_uid    uuid references core.region(region_uid),
  level         text not null check (level in ('band','region','sub_region','zone')),
  created_at    timestamptz not null default now()
);

-- Canonical clinic. Pulse demo codes (DL-RHN-02) and ReputationOS Clove/SAP
-- codes describe the SAME real clinics but with different identifiers, so the
-- canonical row is keyed by a UID and external codes resolve via core.clinic_alias.
create table core.clinic (
  clinic_uid    uuid primary key default gen_random_uuid(),
  canonical_code text unique not null,          -- the agreed code going forward
  name          text not null,
  region_uid    uuid references core.region(region_uid),
  sub_region    text,
  zone          text,
  clinic_head   text,                            -- denormalized for fast reads
  ops_executive text,
  category      text,
  latitude      double precision,
  longitude     double precision,
  created_at    timestamptz not null default now()
);

-- Identity crosswalk: the single most important table for "alignment". Maps a
-- product's external clinic identifier to the canonical clinic. Seed it from
-- the Clove Master Tracker + KML join and the Pulse demo catalogue.
create table core.clinic_alias (
  product       text not null check (product in ('pulse','reputationos','clove','kml')),
  external_code text not null,
  clinic_uid    uuid not null references core.clinic(clinic_uid),
  primary key (product, external_code)
);

-- People / owners across both products: telecalling, cluster ops, regional
-- heads, clinic heads, ops executives, agents, escalation owners.
create table core.actor (
  actor_uid     uuid primary key default gen_random_uuid(),
  code          text unique,                     -- e.g. 'OWNER-NEHA'
  name          text not null,
  role          text not null,                   -- cluster_operations, telecalling, regional_head, clinic_head, ops_executive, agent, system, synthetic_importer
  actor_kind    text not null default 'human' check (actor_kind in ('human','system','synthetic_importer')),
  created_at    timestamptz not null default now()
);

-- -----------------------------------------------------------------------------
-- CORE: provenance, evidence, event spine
-- -----------------------------------------------------------------------------

create table core.ingest_batch (
  batch_id      text primary key,                -- 'BATCH-DEMO-002'
  product       text not null,
  source_system text not null,                   -- crm_export, telephony_export, ...
  ingested_at   timestamptz not null default now(),
  row_count     integer,
  data_quality  text default 'unknown' check (data_quality in ('unknown','low','partial','ready')),
  notes         text
);

-- Universal evidence. Both products cite the same table. `data` holds the
-- structured proof payload; never store clinical notes or raw PII here.
create table core.evidence (
  evidence_id      text primary key,             -- 'EV-CALL-0001'
  product          text not null check (product in ('pulse','reputationos','core')),
  type             text not null,                -- call_log, appointment_record, invoice, ticket_message, sla_timer, ...
  description      text not null,
  url              text,
  data             jsonb not null default '{}'::jsonb,
  source_system    text,
  source_record_id text,
  ingest_batch_id  text references core.ingest_batch(batch_id),
  occurred_at      timestamptz,                  -- when the underlying thing happened (nullable = unknown)
  observed_at      timestamptz not null default now(),
  confidence       text not null default 'unverified' check (confidence in ('unverified','low','medium','high','verified')),
  data_quality     text not null default 'unknown' check (data_quality in ('unknown','low','partial','ready')),
  created_at       timestamptz not null default now()
);

-- Append-only event spine. Every acquisition / contact / appointment / revenue /
-- complaint / SLA / closure / intervention event from BOTH products lands here.
create table core.event (
  event_id       text primary key,
  product        text not null check (product in ('pulse','reputationos')),
  entity_type    text not null,                  -- lead, contact_attempt, appointment, revenue, leakage, ticket, intervention
  entity_id      text not null,
  type           text not null,                  -- SystemIngest, Classification, Routing, SlaBreach, ClosureClaim, AppointmentBooked, RevenueRealized, ...
  payload        jsonb not null default '{}'::jsonb,
  actor_uid      uuid references core.actor(actor_uid),
  clinic_uid     uuid references core.clinic(clinic_uid),
  region_uid     uuid references core.region(region_uid),
  occurred_at    timestamptz,                    -- nullable: unknown real time (honesty rule)
  observed_at    timestamptz not null default now(),
  confidence     text not null default 'unverified',
  approval_state text not null default 'n/a' check (approval_state in ('n/a','proposed','approved','rejected')),
  created_at     timestamptz not null default now()
);
create index on core.event (product, entity_type, entity_id);
create index on core.event (clinic_uid);
create index on core.event (occurred_at);

-- Many-to-many: an event is backed by zero or more evidence rows.
create table core.event_evidence (
  event_id    text not null references core.event(event_id) on delete cascade,
  evidence_id text not null references core.evidence(evidence_id),
  primary key (event_id, evidence_id)
);

-- -----------------------------------------------------------------------------
-- CORE: the shared intervention / closure fabric (the alignment keystone)
-- -----------------------------------------------------------------------------

-- An intervention can hang off a Pulse leakage OR a ReputationOS ticket. Same
-- owners, same statuses, same evidence-backed closure machinery for both.
-- Status set matches the ReputationOS CP-05 accountability state machine so the
-- two products share one closure lifecycle (no direct close; proof + verify).
create table core.intervention (
  intervention_id   text primary key,            -- 'INT-0001'
  subject_type      text not null check (subject_type in ('pulse_leakage','reputationos_ticket')),
  subject_id        text not null,               -- leakage_id or ticket id
  title             text not null,
  owner_uid         uuid references core.actor(actor_uid),
  status            text not null default 'Detected'
                    check (status in ('Detected','Reviewed','Assigned','In Progress','Proof Required','Closure Claimed','Closed','Reopened','Rejected')),
  due_date          date,
  closure_criteria  text not null,
  external_writeback boolean not null default false,  -- MVP rule: never write back to external systems
  notes             jsonb not null default '[]'::jsonb,
  history           jsonb not null default '[]'::jsonb,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now()
);
create index on core.intervention (subject_type, subject_id);
create index on core.intervention (owner_uid);

-- Closure proof state machine. A claim is only as strong as its evidence.
create table core.closure_proof (
  proof_id        text primary key,
  intervention_id text not null references core.intervention(intervention_id) on delete cascade,
  claimed_status  text not null,
  confidence      text not null default 'unverified' check (confidence in ('low','unverified','verified')),
  basis           text not null,
  verified_by     uuid references core.actor(actor_uid),
  created_at      timestamptz not null default now()
);
create table core.closure_proof_evidence (
  proof_id    text not null references core.closure_proof(proof_id) on delete cascade,
  evidence_id text not null references core.evidence(evidence_id),
  primary key (proof_id, evidence_id)
);

-- -----------------------------------------------------------------------------
-- PULSE: RevOps domain (lead -> attended appointment leakage)
-- -----------------------------------------------------------------------------

create table pulse.campaign (
  campaign_id   text primary key,
  platform      text not null,                   -- google, meta
  campaign_name text not null,
  region_uid    uuid references core.region(region_uid),
  spend_inr     integer not null default 0
);

create table pulse.lead (
  lead_id                  text primary key,
  pseudonymous_person_id   text not null,        -- never store name/phone/email here
  campaign_id              text references pulse.campaign(campaign_id),
  channel                  text,
  region_uid               uuid references core.region(region_uid),
  clinic_uid               uuid references core.clinic(clinic_uid),
  created_at               timestamptz not null,
  lead_status              text not null,        -- captured, contacted, appointment_booked, attended, treatment_accepted
  connected                boolean not null default false,
  booked                   boolean not null default false,
  appointment_status       text,
  first_contact_delay_min  integer,
  no_attempt_24h           boolean not null default false,
  source_system            text,
  source_record_id         text,
  ingest_batch_id          text references core.ingest_batch(batch_id)
);
create index on pulse.lead (region_uid, clinic_uid);

create table pulse.contact_attempt (
  attempt_id       text primary key,
  lead_id          text references pulse.lead(lead_id) on delete cascade,
  attempted_at     timestamptz not null,
  outcome          text not null,                -- connected, no_answer, busy, not_connected
  duration_seconds integer not null default 0,
  owner_uid        uuid references core.actor(actor_uid),
  clinic_uid       uuid references core.clinic(clinic_uid),
  source_system    text,
  source_record_id text,
  ingest_batch_id  text references core.ingest_batch(batch_id)
);

create table pulse.appointment (
  appointment_id   text primary key,
  lead_id          text references pulse.lead(lead_id) on delete cascade,
  clinic_uid       uuid references core.clinic(clinic_uid),
  campaign_id      text references pulse.campaign(campaign_id),
  scheduled_for    timestamptz,
  booked_at        timestamptz,
  status           text not null,                -- attended, no_show, cancelled
  source_system    text,
  source_record_id text,
  ingest_batch_id  text references core.ingest_batch(batch_id)
);

create table pulse.revenue (
  revenue_id       text primary key,
  lead_id          text references pulse.lead(lead_id) on delete cascade,
  clinic_uid       uuid references core.clinic(clinic_uid),
  campaign_id      text references pulse.campaign(campaign_id),
  realized_at      timestamptz,
  gross_value_inr  integer,
  net_value_inr    integer,
  status           text,
  source_system    text,
  source_record_id text,
  ingest_batch_id  text references core.ingest_batch(batch_id)
);

-- Detected leakage; the subject of a shared core.intervention.
create table pulse.leakage (
  leakage_id              text primary key,
  type                    text not null,         -- low_contact_rate, slow_first_contact, high_cost_per_attended, ...
  region_uid              uuid references core.region(region_uid),
  clinic_uid              uuid references core.clinic(clinic_uid),
  stage                   text,
  severity                text,                  -- Critical, High, Medium, Low
  severity_score          numeric,
  recoverable_appointments integer,
  recoverable_value_inr    bigint,
  rule_version            text not null,
  data_version            text not null,
  created_at              timestamptz not null default now()
);
create table pulse.leakage_evidence (
  leakage_id  text not null references pulse.leakage(leakage_id) on delete cascade,
  evidence_id text not null references core.evidence(evidence_id),
  primary key (leakage_id, evidence_id)
);

-- -----------------------------------------------------------------------------
-- REPUTATIONOS: complaint / NPS / SLA / accountability domain
-- -----------------------------------------------------------------------------

create table reputationos.sla_policy (
  policy_id        text primary key,
  priority         text not null check (priority in ('P1','P2','P3')),
  target_minutes   integer not null,
  business_calendar text not null default 'default'
);

create table reputationos.ticket (
  id               text primary key,
  source           text,
  channel          text,
  priority         text not null check (priority in ('P1','P2','P3')),
  status           text not null check (status in ('Open','In Progress','Pending Clinic','Closed')),
  clinic_uid       uuid references core.clinic(clinic_uid),
  region_uid       uuid references core.region(region_uid),
  sub_region       text,
  zone             text,
  clinic_head      text,
  ops_executive    text,
  assigned_agent_uid   uuid references core.actor(actor_uid),
  manager_owner_uid    uuid references core.actor(actor_uid),
  escalation_owner_uid uuid references core.actor(actor_uid),
  issue            text,
  latest_comment   text,
  elapsed_minutes  integer not null default 0,
  sla_target_minutes integer not null default 0,
  sla_state        text not null check (sla_state in ('within_sla','approaching_breach','breached')),
  unread           integer not null default 0,
  messages         integer not null default 0,
  risk_signals     text[] not null default '{}', -- missed_ticket, sla_drift, repeat_clinic_complaint, ...
  created_at       timestamptz not null default now(),
  updated_at       timestamptz not null default now()
);
create index on reputationos.ticket (clinic_uid);
create index on reputationos.ticket (status, sla_state);

-- Ticket events also flow into core.event; the discriminated payloads (CP-03
-- event spine: SystemIngest, Classification, Routing, SlaBreach, ClosureClaim,
-- OwnerAssignment, EscalationAction, ProofRequest, ...) carry core.evidence refs.

-- =============================================================================
-- Convenience: a single cross-product intervention view for the Cockpit /
-- accountability queue. One list, both products, same fabric.
-- =============================================================================
create or replace view core.intervention_feed as
select
  i.intervention_id,
  i.subject_type,
  i.subject_id,
  i.title,
  i.status,
  i.due_date,
  a.name as owner_name,
  i.external_writeback,
  i.updated_at
from core.intervention i
left join core.actor a on a.actor_uid = i.owner_uid;

-- =============================================================================
-- Access model (run as separate migration; see README for rationale)
--   role pulse_app          -> usage on core (read) + pulse (read/write) + core.intervention (read/write where subject_type='pulse_leakage')
--   role reputationos_app   -> usage on core (read) + reputationos (read/write) + core.intervention (read/write where subject_type='reputationos_ticket')
--   role analytics_ro       -> read-only on all schemas
-- Enable Row Level Security on core.intervention and core.evidence so a product
-- can only mutate its own subjects. Use Supabase connection POOLER (transaction
-- mode) for serverless callers (Vercel functions); direct 5432 for migrations.
-- =============================================================================
