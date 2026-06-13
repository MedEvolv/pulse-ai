# Pulse-00 — Canonical Revenue Contract

**Status:** v0.1 · 2026-06-13
**Owner doc:** this is the authoritative contract for Pulse AI's revenue model. It pins
the canonical revenue journey, every metric definition, the leakage taxonomy, and the
export contract that the unified database (`docs/unified-database/`) and any consumer
(ReputationOS, analytics, a future ingest pipeline) must honour.

**Source of truth.** The running implementation is `backend/engine.py`. This document
*describes* that engine; it does not redefine it. Every constant, threshold, and formula
below is traced to a symbol in `engine.py`. If the two disagree, the engine wins and this
file is corrected — never the reverse silently. The LLM never computes numbers; it only
narrates facts produced by the engine (`engine.py` module docstring).

**Versioning.** Three version stamps travel with every exported fact:

| Stamp | Symbol (`engine.py`) | Value @ v0.1 | Meaning |
|---|---|---|---|
| `rule_version` | `RULE_VERSION` | `rules-2.0.0` | Leakage rules + severity weights |
| `data_version` | `DATA_VERSION` | `data-1.0.0` | Synthetic generator + seed |
| `period` | `PERIOD` | `2026-06` | Reporting window label |

A change to thresholds, severity weights, or the funnel definition **must** bump
`rule_version`. A change to the generator or seed bumps `data_version`. Consumers key
their caches on `(rule_version, data_version, period)`.

Determinism: `SEED = 42`, no runtime randomness, reference date
`REFERENCE_DATE = 2026-06-13 09:00 IST`; current window = trailing 30 days, prior window =
the 30 days before that.

---

## 1. Canonical revenue journey

The revenue journey is a **four-stage primary funnel**. It ends at **Appointment Attended**
(CP-01.6) — *not* at revenue. Treatment acceptance and realized revenue are **partial
contextual data** drawn from a separate billing source and are never part of the primary
funnel or its conversion math.

| # | Stage | `stage_key` | Count selector | In primary funnel |
|---|---|---|---|---|
| 1 | Leads Captured | `captured` | `compute_metrics.leads` | ✅ |
| 2 | Contacted | `contacted` | `compute_metrics.contacted` | ✅ |
| 3 | Appointment Booked | `appointment_booked` | `compute_metrics.booked` | ✅ |
| 4 | Appointment Attended | `attended` | `compute_metrics.attended` | ✅ |
| — | Treatment Accepted | `treatment_accepted` | `funnel_context.treatment_accepted` | ❌ contextual |
| — | Revenue Realized | — | `funnel_context.revenue_realized_inr` | ❌ contextual |

**Stage-key contract.** `stage_key` is the stable identifier for URL-faithful drilldown
(CP-08) and joins. Stage *labels* are display strings and may change; `stage_key` values
are frozen and exported verbatim. The journey/lead `lead_status` enum is a superset that
also carries the contextual tail: `captured → contacted → appointment_booked → attended →
treatment_accepted` (plus the booking-without-attendance state on the lead record).

**Conversion + leakage flag.** Each funnel stage carries `conversion_rate = count /
previous_count` (null for stage 1), `drop = max(previous − count, 0)`, and a boolean
`leakage = conversion_rate < 0.70`. The 0.70 funnel flag is a *display* heuristic only;
it is **not** the leakage taxonomy in §3 and creates no recoverable pool.

---

## 2. Metric definitions

All metrics come from `compute_metrics(variant, region, clinic)`. Scope is by `region_id`
and/or `clinic_code`; spend is summed from in-scope `CAMPAIGNS`. Rates use `_safe_rate`
(returns `null` when the denominator is 0, else rounded to 4 dp). All money is INR.

| Metric | Field | Definition (numerator / denominator) |
|---|---|---|
| Spend | `spend_inr` | Σ `campaign.spend_inr` in scope |
| Leads | `leads` | count of leads in scope |
| Cost per lead | `cpl_inr` | `spend_inr / leads` (rounded) |
| Contacted | `contacted` | count of leads with `connected = true` |
| **Contact rate** | `contact_rate` | `contacted / leads` |
| Median first-contact delay | `median_first_contact_delay_min` | median of `first_contact_delay_min` over leads that have one |
| Uncontacted ≥24h | `uncontacted_24h` | count of leads with `no_attempt_24h = true` |
| Booked | `booked` | count of leads with `booked = true` |
| **Booking rate** | `booking_rate` | `booked / contacted` |
| Scheduled | `scheduled` | count of appointments for in-scope leads |
| Attended | `attended` | appointments with `status = attended` |
| No-show | `no_show` | appointments with `status = no_show` |
| Cancelled | `cancelled` | appointments with `status = cancelled` |
| **Show rate** | `show_rate` | `attended / scheduled` |
| Cost per attended | `cost_per_attended_inr` | `spend_inr / attended` (rounded) |
| Treatments | `treatments` | count of revenue rows (contextual) |
| Revenue | `revenue_inr` | Σ `revenue.net_value_inr` (contextual) |

**Denominator discipline (frozen):** contact rate is over **leads**, booking rate is over
**contacted** (not leads), show rate is over **scheduled** (not booked). These three chained
denominators are the backbone of the non-overlapping opportunity math in §4 — consumers must
not re-base them.

### 2.1 Benchmarks

`benchmark_rates()` provides one benchmark per stage metric. The benchmark `type` is
`best_comparable_region` — the best-performing region's value for that metric in the same
period (`best_benchmark`; for `cost_per_attended_inr`, "best" = lowest, all others = highest).
Every benchmark carries the caveat *"Best comparable synthetic region for the same period."*
Benchmarks are assumptions, not forecasts.

### 2.2 Aggregate metric evidence (CP-06)

`build_metric_evidence()` emits one `MetricEvidence` record per **stage × region**
(`contact`, `booking`, `show`), id `MEV-{region}-{STAGE}-{period}`, carrying: `metric_id`,
`numerator`, `denominator`, `value`, `cohort_definition`, `cohort_hash`
(`sha256:` of sorted lead ids), `affected_record_count`, up to 8 `sample_affected_record_ids`,
`source_batch_ids`, and `limitations` (`["Synthetic data", "First-touch attribution"]`).
Every recoverable claim in §3/§4 must reference a `metric_evidence_id`. A claim with no
metric evidence is diagnostic only.

---

## 3. Leakage taxonomy

Leakages come from `build_leakages()`, ids `LEAK-NNN`, sorted by `severity_score` desc.
Each leakage declares an **`opportunity_relationship`** that governs whether its recoverable
value may be summed:

- **`shared`** — references a regional opportunity group (§4). Multiple alerts can share one
  group; the group is counted **once**.
- **`allocation`** — a clinic-level sub-pool carved out of a regional pool. Never additive
  with its parent or with sibling allocations.
- **`diagnostic`** — creates **no** recoverable pool (`recoverable_value_inr = 0`). Context only.

**Alerts are never additive in the summary; only unique opportunity groups are**
(`is_additive_in_summary` defaults to `false` on every alert).

| ID | `type` | Scope | Stage | Trigger (from `engine.py`) | Relationship |
|---|---|---|---|---|---|
| L-01 | `slow_first_contact` | region | contact | median first-contact delay > 120 min **OR** uncontacted-24h share > 0.20 | shared (contact) |
| L-02 | `low_contact_rate` | region | contact | (benchmark − contact_rate) ≥ 0.10 and leads ≥ 20 | shared (contact) |
| L-03 | `contact_to_booking_drop` | region | booking | (benchmark − booking_rate) ≥ 0.12 **and** contact not already breached | shared (booking) |
| L-04 | `high_no_show_rate` | clinic | show | clinic show_rate < 0.65 and scheduled ≥ 15 | allocation (show) |
| L-05 | `high_cost_per_attended` | region | attended | CPA > 1.35 × comparable-region median and attended ≥ 10 | diagnostic |
| L-06 | `clinic_concentration` | clinic | show | one clinic holds > 35% of regional recoverable and ≥ 4 recoverable appts | allocation (show, shares L-04 group) |
| L-08 | `repeat_complaint_context` | clinic | attended | ≥ 3 SLA-breached reputation events at a clinic | diagnostic |

Notes that are part of the contract:
- **L-03 guard:** suppressed when contact is already breached, so a region is not double-charged
  for the same upstream loss.
- **L-05 & L-08 are diagnostic by construction** — they carry `recoverable_value_inr = 0` and
  must never enter a value rollup. L-05 instead reports `excess_cost_inr`. L-08 is explicitly
  *"Contextual signal only — NOT the proven cause of acquisition leakage."*
- **L-06 shares L-04's clinic show allocation group** — the two reference the same
  `opportunity_group_id`; counting both would double-count.
- There is no `L-07` in the current rule set.

### 3.1 Severity

`_severity` blends four 0–100 sub-scores with fixed weights (`SEVERITY_WEIGHTS`):
`impact 0.45 · deviation 0.30 · confidence 0.15 · ownership 0.10`. Bands:
`≥85 Critical · ≥70 High · ≥45 Medium · else Low`. Impact is scaled from recoverable value
(`_impact = min(100, recoverable_value_inr / 2200)`). Each leakage exports the four sub-scores
in `severity_breakdown`. Changing any weight or band bumps `rule_version`.

### 3.2 Ownership

Each leakage names an `owner_role` from the canonical role set: `cluster_operations`,
`telecalling`, `regional_head` (clinic-level alerts may resolve to `clinic_head`). Roles map to
`core.actor.role` in the unified schema.

---

## 4. Opportunity model (non-overlapping)

The **only additive pools** are the regional opportunity groups from
`region_opportunity_groups(region)`. For a region with leads `L`, current rates `C/B/S`
(contact/booking/show) and benchmarks `Cb/Bb/Sb`, the **non-overlapping** marginal attended
appointments are:

```
contact group = L · max(0, Cb−C) · B  · S
booking group = L · Cb · max(0, Bb−B) · S
show group    = L · Cb · Bb · max(0, Sb−S)
```

Each subsequent stage is multiplied by the *current* rate of the stages it has already passed
and the *benchmark* rate of the stages above it — so the three pools partition the gap and never
overlap. A group with raw value ≤ 0.01 is dropped. Display counts use one shared rounding
function (`display_round`); value = `display_additional_attended × avg_realized_value`
(`DEFAULT_AVG_REALIZED_VALUE = 17500` INR, override via the simulation input).

- `regional_opportunity_summary(region)` sums **only** these unique groups → the waterfall total.
  It carries the standing caveat: *"Scenario opportunity based on explicit benchmark assumptions.
  Not a forecast or causal revenue estimate. Not additive across related alerts."*
- `clinic_show_allocation(region)` splits the regional **show** group across clinics by
  recoverable weight, **capped so the running total never exceeds the regional pool**. Each clinic
  allocation is `is_additive_in_summary = false` with a `parent_opportunity_group_id`.

**Rollup rule for any consumer:** sum `value_inr` over opportunity groups where
`is_additive_in_summary = true` and each `opportunity_group_id` appears once. Never sum alert
`recoverable_value_inr`, never add allocations to their parent, never add diagnostic alerts.

---

## 5. Export contract

This is the stable shape Pulse AI exposes and the unified DB ingests. The wire entities below
are the contract; field names match `engine.py` output and map 1:1 to the unified schema
(`docs/unified-database/schema.sql`). Adapters translate identifiers (codes → `*_uid`) but must
not rename or re-base fields.

### 5.1 Entity → table mapping

| Wire entity | Engine producer | Unified table |
|---|---|---|
| Region | `REGION_DEFS` | `core.region` |
| Clinic | `CLINICS` | `core.clinic` (+ `core.clinic_alias`) |
| Owner / actor | `OWNERS` | `core.actor` |
| Campaign | `CAMPAIGNS` | `pulse.campaign` |
| Lead | `dataset.leads[]` | `pulse.lead` |
| Contact attempt | `dataset.attempts[]` | `pulse.contact_attempt` |
| Appointment | `dataset.appointments[]` | `pulse.appointment` |
| Revenue | `dataset.revenues[]` | `pulse.revenue` |
| Reputation event | `dataset.reputations[]` | `reputationos.ticket` (context) |
| Evidence (record + metric) | `get_evidence_index`, `build_metric_evidence` | `core.evidence` |
| Leakage | `build_leakages()` | `pulse.leakage` (+ `pulse.leakage_evidence`) |
| Intervention | `/api/interventions` | `core.intervention` (+ `closure_proof`) |

### 5.2 Identity & provenance rules (frozen)

- **Identity resolves through the crosswalk.** Pulse demo codes (`DL-RHN-02`, `OWNER-NEHA`,
  `REG-NORTH`) are *external* identifiers; they resolve to `core.clinic.clinic_uid` /
  `core.actor.actor_uid` / `core.region.region_uid` via `core.clinic_alias` and the analogous
  actor/region maps. Consumers join on the UID, never on the demo code. (Crosswalk build = the
  next Track B deliverable.)
- **Provenance is mandatory.** Every record carries `source_system`, `source_record_id`, and
  `ingest_batch_id`. Every derived claim carries `rule_version` + `data_version` + `period` and at
  least one `evidence_id`.
- **Honesty fields.** `occurred_at` may be null when the real time is unknown; `confidence` and
  `data_quality` default to the lowest trustworthy value. A claim's strength never exceeds its
  evidence's `confidence`.

### 5.3 Privacy boundary (frozen, from the convergence decision)

- Leads carry only `pseudonymous_person_id` — **never** name / phone / email / clinical notes.
- Raw SAP / Clove codes are an **internal join key only** and must never render on demo or
  external surfaces.
- `external_writeback = false` for the MVP: Pulse never writes back to source systems.
- The LLM receives only engine-produced facts + evidence ids; it never sees raw PII and never
  computes numbers.

### 5.4 Stability guarantees

Frozen for v0.1 (changing any of these bumps `rule_version` and requires a consumer note):
the four primary `stage_key` values; the three chained denominators (§2); the non-overlapping
opportunity formula (§4); the `opportunity_relationship` semantics (`shared` / `allocation` /
`diagnostic`); the severity weights and bands (§3.1); the additivity rollup rule (§4).

---

## 6. What Pulse-00 unblocks

With the journey, metrics, taxonomy, and export contract pinned, the remaining Track B
deliverable is the **identity crosswalk** — seeding `core.region`, `core.clinic`,
`core.clinic_alias`, and `core.actor` so the demo codes above resolve to the same canonical
rows ReputationOS uses (Clove Master Tracker + KML, 576 clinics). Until that crosswalk exists,
"shared database" is aspirational; §5.2 is the contract it must satisfy. Provisioning the
Supabase project stays gated (unified-database README §7) until the crosswalk lands.
