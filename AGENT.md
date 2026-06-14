# Pulse AI - Canonical Agent Handoff

Last updated: 2026-06-14

This file is the operational memory and instruction layer for every agent that
works in this repository. Read it before planning, editing, testing, committing,
or deploying Pulse AI.

It records the product intent, technical architecture, implementation history,
truth boundaries, known risks, verification state, competitive positioning,
demo narrative, and next decisions. Do not replace it with a shorter generic
README.

---

## Agent skills

Per-repo config consumed by the engineering skills (`to-issues`, `to-prd`, `triage`,
`diagnose`, `tdd`, `improve-codebase-architecture`, `zoom-out`).

### Issue tracker

Issues live as GitHub issues on `MedEvolv/pulse-ai` (via the `gh` CLI). The vault + this
AGENT.md remain the strategic record; issues are discrete grabbable work. See `docs/agents/issue-tracker.md`.

### Triage labels

Canonical five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`,
`ready-for-human`, `wontfix`); labels created on first triage use. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context. `CONTEXT.md` + `docs/adr/` created lazily by `/grill-with-docs`; until then
the domain glossary is `docs/pulse-00-canonical-contract.md`. See `docs/agents/domain.md`.

---

## 1. Source of Truth

Repository:

- GitHub: `https://github.com/MedEvolv/pulse-ai`
- Canonical local checkout: `C:\ArchLife-Systems\pulse-ai`
- Branch: `main`
- Current observed commit when this file was written:
  `b013c41 docs: unified database plan for ReputationOS + Pulse AI`

Vault project:

- `C:\Users\ishaa\edocsil-cas\01_Projects\ReputationOps_Mirror`

Important vault artifacts:

- `prd--pulse-ai-emergent-hackathon-mvp-v0.1.md`
- `prd--pulse-ai-emergent-correction-pack-v0.2.md`
- `decision--pulse-ai-product-convergence-v0.1.md`
- `research--pulse-ai-competitive-landscape-2026-06-13.md`
- `architecture--unified-database-reputationos-pulse-ai-2026-06-13.md`
- `call-notes--vikram-2026-06-12-two-calls.md`
- `current-status.md`
- `next-actions.md`

Repository-local product memory:

- `memory/PRD.md`

Unified database design:

- `docs/unified-database/README.md`
- `docs/unified-database/schema.sql`
- `docs/unified-database/seed-crosswalk.sql` (identity crosswalk seed, v0.1)
- `docs/unified-database/crosswalk.md` (crosswalk reconciliation + scale-up path)
- `docs/pulse-00-canonical-contract.md` (Pulse-00 — canonical revenue contract)

If this file conflicts with current source code, inspect and test the source
before changing this file. If it conflicts with a newer explicit decision from
Dr. Ishaan Wadhwa, the newer decision wins and this file must be updated.

---

## 2. Product Identity

### 2.1 Name

Pulse AI.

### 2.2 Category

Revenue Operations intelligence and accountability layer.

### 2.3 Core positioning

> The real-time intelligence layer between raw revenue data and sales
> execution.

For the hackathon MVP, "real-time" is an aspiration and product direction. The
implemented proof uses deterministic synthetic data and should not be described
as a live production integration.

### 2.4 Core problem

Management teams use fragmented systems:

- Meta and Google lead dashboards;
- CRM;
- telephony;
- appointment or operational systems;
- campaign reports;
- manually assembled spreadsheets and presentations.

This fragmentation causes:

- no coherent 360-degree lead journey;
- delayed decisions;
- weak context during live management reviews;
- leakage between lead capture and human follow-up;
- unclear operational ownership;
- repetitive manual reporting;
- AI summaries that are difficult to trust because their source calculations
  are opaque.

### 2.5 Product objective

Pulse AI should reconstruct the journey from acquisition to outcome, identify
where conversion is leaking, explain why it matters, assign an accountable
owner, and require evidence before the intervention is considered closed.

The broad vision covers CAC to LTV.

The current MVP intentionally proves a narrower journey:

```text
Lead captured
    -> Contacted
    -> Appointment booked
    -> Appointment attended
```

Do not claim complete CAC-to-LTV intelligence until treatment, invoice,
retention, and realized revenue sources are separately connected and validated.

### 2.6 Primary users

- regional heads;
- marketing heads;
- sales heads;
- finance leaders;
- customer-success leaders;
- operations leaders.

### 2.7 Secondary users

- CEO;
- COO;
- CMO;
- CXO leadership;
- territory managers;
- cluster operations;
- telecalling managers.

### 2.8 Initial design-partner context

The product has been shaped through conversations with Vikram and through
healthcare/multi-clinic operating realities. The implemented demo therefore
uses:

- Indian regions and names;
- clinics;
- paid healthcare leads;
- telecalling;
- appointments;
- attendance;
- regional and clinic accountability.

The architecture can later generalize to other lead-driven sectors, but agents
must not erase the healthcare proof merely to make the copy sound generic.

---

## 3. Relationship to ReputationOS

Pulse AI and ReputationOS are related but not identical.

### 3.1 Pulse AI

Pulse AI is the proposed Revenue Operations umbrella:

- acquisition;
- lead journey;
- contactability;
- booking;
- attendance;
- CAC/CPL/conversion;
- leakage;
- opportunity;
- intervention;
- executive synthesis.

### 3.2 ReputationOS

ReputationOS remains:

- separately sellable;
- a complaints, reviews, NPS, SLA, and accountability module;
- an operational truth layer over incumbent ORM/helpdesk workflows;
- a reusable ownership, evidence, intervention, escalation, and closure fabric.

### 3.3 Shared doctrine

Both products share:

- deterministic facts before AI interpretation;
- evidence references;
- source transparency;
- confidence and caveats;
- explicit ownership;
- human approval;
- closure proof;
- no autonomous external writeback in the MVP.

### 3.4 Data convergence direction

The proposed future architecture is one Supabase/Postgres project with:

- `core` schema for shared entities and accountability fabric;
- `pulse` schema for revenue operations;
- `reputationos` schema for tickets, SLA, reviews, complaints, and reputation.

The alignment keystone is `core.intervention`.

The hard prerequisite is clinic and actor identity reconciliation:

```text
Pulse demo clinic code
    -> core.clinic_alias
    -> canonical core.clinic
    <- core.clinic_alias
    <- ReputationOS / Clove / SAP clinic code
```

Do not claim that both products use one shared database until:

- a database project exists;
- schema migrations are applied;
- both applications use adapters against it;
- clinic aliases resolve to canonical rows;
- owner and region mappings are reconciled;
- read/write behavior is tested.

The database plan is currently proposed documentation. It has not been applied
to a live database.

---

## 4. Competitive Context

Products studied:

- Artisan;
- Gong;
- Gojiberry AI;
- MoEngage;
- CleverTap.

Important distinction:

- Gong specializes in conversation/revenue intelligence.
- Artisan and Gojiberry emphasize AI-led sales execution and outreach.
- MoEngage and CleverTap specialize in customer engagement, segmentation, and
  lifecycle orchestration.

Pulse AI should not imitate all of them at once.

Its differentiating wedge is:

> Evidence-backed leakage intelligence plus accountable intervention closure
> across fragmented revenue systems.

The product should answer four questions:

1. Where is the journey leaking?
2. What deterministic evidence supports that conclusion?
3. Who owns the next intervention?
4. What proof is required before closure?

---

## 5. Current MVP Promise

The current application may truthfully claim:

> Pulse AI reconstructs a synthetic healthcare lead-to-attendance journey,
> detects operational leakage using deterministic rules, calculates
> non-overlapping stage opportunity, and uses an evidence-bound assistant to
> explain what changed and what a human operator should review next.

It must not claim:

- real customer data;
- live Meta, Google, CRM, or telephony connections;
- causal revenue uplift;
- production forecasts;
- autonomous actions;
- validated treatment conversion;
- complete CAC-to-LTV;
- externally certified AI reliability;
- production multi-tenant security;
- a live unified database with ReputationOS.

---

## 6. Technology Stack

### 6.1 Backend

- Python;
- FastAPI `0.115.6`;
- Uvicorn `0.34.0`;
- Pydantic `2.10.4`;
- Motor `3.6.0`;
- MongoDB for mutable intervention/session state (legacy; superseded by the
  repository seam, ADR-0002);
- deterministic synthetic engine for source data and metrics.
- Emergent removed (ADR-0006): no `emergentintegrations` dependency.

### 6.2 Frontend

- React `18.3.1`;
- React Router `6.27.0`;
- Create React App / `react-scripts 5.0.1`;
- Tailwind CSS `3.4.14`;
- Axios;
- Lucide icons.

### 6.3 Model

- Vertex AI Gemini (`gemini-2.5-flash`) via the `google-genai` SDK behind the
  `briefing._complete()` seam (ADR-0007; Emergent removed, ADR-0006); deterministic
  until an `LLM_API_KEY` (Vertex express key) is set;
- model usage off by default;
- deterministic response always available;
- explicit model request required;
- output must pass strict validation.

### 6.4 Future database direction

- Supabase Postgres;
- pooled serverless connection;
- Python adapter for Pulse AI;
- Prisma or `supabase-js` for ReputationOS;
- append-only canonical event spine;
- relational evidence, intervention, and closure records.

This is not implemented yet.

---

## 7. Repository Map

```text
backend/
  server.py
  engine.py
  briefing.py
  brief_validation.py
  model_budget.py
  evaluation.py
  requirements.txt
  tests/
    conftest.py
    test_pulse_api.py

frontend/
  src/
    App.js
    components/
      BriefPanel.js
      EvidenceDrawer.js
      Funnel.js
      Layout.js
      MetricTile.js
      ui.js
    context/
      FilterContext.js
    lib/
      api.js
      format.js
    pages/
      Cockpit.js
      Journeys.js
      JourneyDetail.js
      Leakages.js
      LeakageDetail.js
      Simulation.js
      DataQuality.js
      Evaluation.js

docs/
  unified-database/
    README.md
    schema.sql

memory/
  PRD.md

test_reports/
  iteration_1.json
  iteration_2.json
  pytest/
    pulse_api.xml

.emergent/
  emergent.yml
```

An unrelated tracked file exists at repository root:

- `two face dialectics.jpg`

It predates the correction packet and does not belong to the product codebase.
Do not delete it without explicit approval. Recommend moving it to the vault in
a separate cleanup.

Current untracked generated directories observed when this file was written:

- `backend/.vercel/`
- `frontend/.vercel/`

Do not commit them. Confirm and remove them only as a bounded generated-artifact
cleanup.

---

## 8. Synthetic Dataset

### 8.1 Purpose

The dataset exists to demonstrate the operating logic safely:

- no real patient data;
- no direct identifiers;
- no clinical notes;
- deterministic and reproducible;
- deliberate regional performance variation;
- enough records to support drilldowns and leakage examples.

### 8.2 Current dimensions

- 240 synthetic leads;
- three regions:
  - `REG-NORTH`;
  - `REG-WEST`;
  - `REG-SOUTH`;
- clinics under each region;
- Google and Meta campaigns;
- contact attempts;
- appointment records;
- limited revenue/context records;
- evidence objects;
- intervention owners.

### 8.3 Current reporting period

- `PERIOD = "2026-06"`
- data version: `data-1.0.0`
- rules version: `rules-2.0.0`
- prompt version: `brief-2.0.0`
- evaluation version: `eval-2.0.0`

### 8.4 Campaign examples

- North Search Implant;
- North Social Smile;
- West Search Implant;
- West Social Smile;
- South Search Implant;
- South Social Smile.

### 8.5 Privacy boundary

Only pseudonymous record IDs should appear:

- lead ID;
- campaign ID;
- clinic code;
- region ID;
- evidence ID;
- metric ID;
- owner ID.

Do not add:

- patient name;
- phone;
- email;
- Aadhaar;
- postal address;
- date of birth;
- clinical diagnosis;
- treatment notes.

---

## 9. Deterministic Metric Engine

`backend/engine.py` is the source of truth for:

- synthetic source generation;
- cohort selection;
- metrics;
- funnel;
- benchmarks;
- opportunity groups;
- clinic allocation;
- leakage rules;
- evidence index;
- affected records.

AI output must never become the source of truth for these calculations.

### 9.1 Primary metrics

- leads;
- contacted;
- booked;
- attended;
- contact rate;
- booking rate;
- show rate;
- spend;
- CPL;
- cost per attended;
- first-contact delay;
- uncontacted after 24 hours;
- no-show count/rate.

### 9.2 Primary funnel

```text
Leads Captured
Contacted
Appointment Booked
Appointment Attended
```

Treatment accepted and revenue realized must not appear as duplicate funnel
stages when backed by the same count.

### 9.3 Benchmark approach

The current synthetic proof compares each region against the best comparable
synthetic region or configured target.

Every benchmark claim should retain:

- benchmark type;
- source region/target;
- value;
- period;
- caveat.

---

## 10. Economic Truth: Opportunity Waterfall

This was a major v0.2 correction.

The first implementation reused one show-rate recovery estimate across several
alerts. That made multiple cards look independently additive even when they
described the same opportunity.

The corrected design uses non-overlapping stage pools.

Let:

```text
L  = leads
C  = current contact rate
B  = current booking rate
S  = current show rate
Cb = benchmark contact rate
Bb = benchmark booking rate
Sb = benchmark show rate
```

Contact opportunity:

```text
L * max(0, Cb - C) * B * S
```

Booking opportunity:

```text
L * Cb * max(0, Bb - B) * S
```

Show opportunity:

```text
L * Cb * Bb * max(0, Sb - S)
```

Total:

```text
contact opportunity + booking opportunity + show opportunity
```

### 10.1 Rules

- Only unique regional stage opportunity groups are additive.
- Related alerts may share one opportunity group.
- Leakage cards themselves must never be naively summed.
- High cost per attended is diagnostic and creates no separate recovery pool.
- Clinic no-show opportunities are allocations of the regional show pool.
- Clinic allocations must never exceed the regional show pool.
- Values are scenarios based on benchmark assumptions, not forecasts.

### 10.2 Copy boundary

Use:

> Scenario opportunity based on explicit benchmark assumptions. Not a forecast
> or causal revenue estimate.

### 10.3 Reported North correction

The repository product memory records:

- old naive overlap: approximately INR 7.175 lakh across repeated alert values;
- corrected unique pools:
  - contact: 15 appointments / INR 2.625 lakh;
  - booking: 4 appointments / INR 0.70 lakh;
  - show: 14 appointments / INR 2.45 lakh;
- total: 33 appointments / INR 5.775 lakh.

These numbers are implementation-memory values. Recompute and test them if
engine inputs change.

---

## 11. Leakage Model

Current leakage categories include:

- slow first contact;
- low contact rate;
- contact-to-booking drop;
- high no-show rate;
- high cost per attended;
- clinic concentration;
- reputation context.

Each leakage should expose:

- leakage ID;
- region;
- optional clinic;
- stage;
- metric ID;
- observed value;
- threshold;
- benchmark;
- severity;
- owner role;
- confidence;
- caveats;
- aggregate metric evidence;
- affected cohort;
- opportunity group relationship;
- whether it is additive.

### 11.1 Opportunity relationships

- `shared`: multiple alerts describe the same regional stage pool;
- `allocation`: clinic opportunity is a subdivision of a regional pool;
- `diagnostic`: no recovery pool is created.

Every alert currently has `is_additive_in_summary=false`.

Regional summaries use unique opportunity groups instead.

---

## 12. Evidence Model

Evidence is not decorative. It is part of the product contract.

### 12.1 Evidence types

- aggregate metric evidence;
- pseudonymous call/contact records;
- pseudonymous appointment records;
- campaign/spend context;
- source batch metadata.

### 12.2 Aggregate metric evidence

A metric evidence record should carry:

- evidence ID;
- metric ID;
- region;
- optional clinic;
- period;
- numerator;
- denominator;
- value;
- source batch IDs;
- cohort definition;
- stable cohort hash;
- affected-record count;
- sample affected pseudonymous IDs;
- limitations.

### 12.3 Cohort-faithfulness

Every cited record must belong to the actual affected cohort.

Do not select the first arbitrary records from a region merely because they are
available.

### 12.4 Model boundary

The model may cite only:

- metric IDs included in the exact prompt facts;
- evidence IDs included in the exact prompt facts.

An ID that exists elsewhere on the server but was not in the prompt is not
allowed.

---

## 13. Briefing Agent

### 13.1 Role

The current bounded agent is the Regional Leakage Briefing Agent.

It:

- summarizes deterministic facts;
- highlights the most material leakage;
- explains why it matters;
- recommends human-reviewed next steps;
- cites deterministic metrics and evidence.

It does not:

- calculate source metrics;
- invent numbers;
- create business plans;
- execute campaigns;
- contact leads;
- update external CRM;
- close interventions;
- make autonomous decisions.

### 13.2 Default behavior

Deterministic mode is the default.

Page load and suggested-question selection must not consume a model run.

The user must explicitly choose:

- `Run AI synthesis`.

### 13.3 Strict output validation

`backend/brief_validation.py` enforces:

- Pydantic schema;
- extra fields forbidden;
- evidence allowlist;
- metric allowlist;
- non-empty evidence;
- non-empty metrics for findings;
- confidence ceiling;
- privacy;
- no autonomous action;
- no ungrounded numbers;
- bounded string and array lengths.

### 13.4 Confidence

Allowed:

- high;
- medium;
- low;
- unverified.

The model may not increase confidence beyond the deterministic ceiling.

### 13.5 Failure behavior

On schema, privacy, provenance, numeric, provider, timeout, cooldown, or budget
failure:

- discard the complete model response;
- return deterministic fallback;
- expose a bounded reason code;
- never expose raw provider exceptions.

Reason-code family includes:

- `MODEL_DISABLED`;
- `MODEL_BUDGET_EXHAUSTED`;
- `MODEL_COOLDOWN_ACTIVE`;
- `MODEL_TIMEOUT`;
- `MODEL_OUTPUT_SCHEMA_FAILED`;
- `MODEL_OUTPUT_PROVENANCE_FAILED`;
- `MODEL_OUTPUT_PRIVACY_FAILED`;
- `MODEL_OUTPUT_NUMERIC_FAILED`;
- `MODEL_PROVIDER_ERROR`.

---

## 14. Model Spend Controls

`backend/model_budget.py` defines:

```text
MODEL_ENABLED=false
MODEL_DAILY_RUN_LIMIT=25
MODEL_MIN_SECONDS_BETWEEN_RUNS=20
MODEL_TIMEOUT_SECONDS=12
MODEL_CACHE_TTL_SECONDS=86400
MODEL_MAX_OUTPUT_TOKENS=700
```

Rules:

- disabled by default;
- server-side daily count;
- cooldown;
- normalized request/facts cache;
- cache hit does not consume a new run;
- timeout;
- bounded tokens;
- deterministic fallback;
- no browser-trusted budget count.

The product can function completely without model access.

Do not remove deterministic mode to make the AI feel more central.

---

## 15. Honest Evaluation

`backend/evaluation.py` implements the offline evaluation harness.

### 15.1 Name

Canonical name:

- `Offline Evaluation Score`.

Required disclaimer:

> This score measures the current build against synthetic offline fixtures. It
> is not a production accuracy claim.

### 15.2 Current fixture count

Twenty adversarial cases.

They cover:

- valid grounded brief;
- no-show brief;
- invented evidence;
- invented metric;
- empty evidence;
- ungrounded/conflicting number;
- email;
- grouped Indian mobile;
- spaced Aadhaar-like number;
- nested patient-name key;
- benign campaign wording;
- unsupported strategic question;
- confidence escalation;
- autonomous action;
- provider timeout;
- malformed output;
- extra schema key;
- honest abstention;
- excessive question length;
- exhausted model budget.

### 15.3 Scoring dimensions

- schema compliance;
- provenance validity;
- numeric fidelity;
- privacy safety;
- abstention correctness;
- action-boundary compliance;
- deterministic fallback correctness;
- role relevance.

No score may be hardcoded.

### 15.4 Release gate

- privacy: 100%;
- provenance: 100%;
- action boundary: 100%;
- overall: at least 90%;
- zero unhandled exceptions.

### 15.5 Current labeling inconsistency

The Evaluation page logic uses the corrected name, but
`frontend/src/components/Layout.js` still labels the navigation item
`Agent Reliability`.

Change it to `Evaluation` or `Offline Evaluation`.

Do not imply externally certified reliability.

---

## 16. Intervention Accountability

Pulse AI does not stop at insight. It creates a human-owned intervention.

### 16.1 State machine

```text
Detected
  -> Reviewed
  -> Assigned
  -> In Progress
  -> Proof Required
  -> Closure Claimed
  -> Closed
```

Additional paths:

- rejected;
- reopened;
- returned to review or active work.

### 16.2 Critical rule

There is no direct close.

`Closure Claimed` requires proof.

`Closed` requires a separate verification action.

### 16.3 Proof

Proof may include:

- metric ID;
- metric evidence ID;
- before and after values;
- threshold;
- review-window dates;
- consecutive compliant days;
- evidence IDs;
- note.

Current required consecutive days:

- five.

### 16.4 Separation of roles

The data model distinguishes:

- owner/claimant;
- verifier.

Do not collapse proof submission and verification into one click.

### 16.5 External writeback

`external_writeback=false`.

No intervention action should update a customer CRM, ad platform, telephony
system, or other external system in the MVP.

---

## 17. Anonymous Demo Sessions

No login is required for the hackathon demo.

Mutable state is isolated through:

- browser-generated UUID;
- local storage key;
- `X-Demo-Session-ID` request header;
- session-scoped interventions;
- session-scoped proof records;
- session-scoped model budget.

The deterministic source dataset remains shared.

### 17.1 Default fallback

When no header is present:

- `shared-demo`.

Agents should avoid relying on `shared-demo` during parallel tests.

### 17.2 Reset

`POST /api/session/reset` resets only the current session’s mutable records.

### 17.3 Test behavior

Use a fresh session ID for each proof-flow browser test.

Do not interpret a previously mutated session as a product defect without
resetting or selecting a fresh session.

---

## 18. Frontend Routes

```text
/                  -> /cockpit
/cockpit           Revenue Cockpit
/journeys          Lead Journey Explorer
/journeys/:leadId  Lead Journey Detail
/leakages          Leakage Queue
/leakages/:id      Leakage Detail + intervention/proof workflow
/simulation        Scenario Simulator
/data-quality      Data Quality and developer transparency
/evaluation        Offline Evaluation
```

Unknown routes redirect to `/cockpit`.

### 18.1 Navigation

Desktop:

- left navigation.

Mobile:

- fixed bottom navigation.

### 18.2 URL state

Journey drilldowns must preserve:

- region;
- stage;
- clinic;
- leakage flag where relevant.

The Journeys page should initialize from URL parameters and keep controls and
the URL synchronized.

---

## 19. Frontend Screens

### 19.1 Revenue Cockpit

Shows:

- regional context;
- headline metrics;
- primary funnel;
- non-overlapping opportunity summary;
- related leakage alerts;
- AI/deterministic briefing;
- drilldowns.

### 19.2 Journeys

Shows:

- pseudonymous lead rows;
- campaign;
- channel;
- clinic;
- creation/contact timing;
- connection;
- appointment status;
- current stage;
- leakage flags.

### 19.3 Journey Detail

Shows:

- current stage;
- timeline;
- source evidence;
- campaign/contact/appointment context;
- leakage flags.

### 19.4 Leakage Queue

Shows:

- severity;
- region/clinic;
- metric;
- stage;
- owner;
- opportunity relationship;
- non-additive or diagnostic state.

### 19.5 Leakage Detail

Shows:

- observed metric;
- threshold;
- benchmark;
- economic arithmetic;
- evidence;
- affected cohort;
- intervention;
- owner;
- status timeline;
- proof claim;
- verification.

### 19.6 Simulation

Allows bounded changes to:

- contact rate;
- booking rate;
- show rate;
- average realized value.

It is deterministic and must be labeled:

- not a forecast.

### 19.7 Data Quality

Should expose:

- source readiness;
- data version;
- rules version;
- period;
- evidence/source limitations;
- model budget state;
- synthetic-data boundary;
- demo reset.

### 19.8 Evaluation

Shows:

- executed case count;
- passed and failed cases;
- dimension scores;
- overall score;
- release readiness;
- exact disclaimer;
- optional model evaluation not executed by default.

---

## 20. Backend API

Current routes:

```text
GET  /api/health
GET  /api/meta
GET  /api/cockpit
GET  /api/opportunity
POST /api/brief
GET  /api/model-budget
GET  /api/leakages
GET  /api/leakages/{leakage_id}
GET  /api/journeys
GET  /api/journeys/{lead_id}
POST /api/simulation
GET  /api/data-quality
GET  /api/evaluation
GET  /api/interventions
POST /api/interventions
PATCH /api/interventions/{intervention_id}
POST /api/interventions/{intervention_id}/proof
POST /api/interventions/{intervention_id}/verify
POST /api/session/reset
```

### 20.1 Request validation

Server-side Pydantic validation must remain authoritative.

Validate:

- known regions;
- known clinics where accepted;
- known owner IDs;
- status transitions;
- question length;
- simulation bounds;
- proof bounds;
- evidence list size;
- date/string lengths.

### 20.2 Known validation divergence

The correction PRD asked for simulation levers from 0 to 15 percentage points
and average value greater than zero up to INR 1,000,000.

The current server code permits:

- improvement up to 100;
- average value from zero up to INR 10,000,000.

The frontend slider remains narrower, but the API is broader.

This is a remaining contract inconsistency. Correct the backend bounds unless a
new product decision explicitly expands them.

### 20.3 CORS

Current design:

- configurable origins;
- credentials disabled;
- header-based demo sessions.

Do not enable wildcard credentialed CORS.

---

## 21. Error Handling

Expected errors should be bounded and user-safe.

Never return:

- stack trace;
- API key;
- connection string;
- full provider error;
- full model response;
- direct identifiers.

Provider/model failures should become deterministic fallback reason codes.

Frontend failure states should:

- be visible;
- offer retry where meaningful;
- not leave stale output looking current.

---

## 22. Tests and Verification

### 22.1 Reported current status

`test_reports/iteration_2.json` reports:

- backend: 24/24 passing;
- frontend: 100% of listed flows;
- no critical defects;
- model disabled in offline tests;
- session-isolated proof flow;
- successful build.

`test_reports/pytest/pulse_api.xml` records:

- 24 tests;
- zero failures;
- zero errors.

### 22.2 Current backend test coverage

- waterfall telescopes to benchmark delta;
- only unique pools additive;
- alerts non-additive;
- CPA diagnostic;
- clinic allocation cap;
- high-severity North examples;
- funnel ending at attended;
- cohort-faithful metric evidence;
- valid brief;
- invented evidence rejection;
- empty evidence rejection;
- ungrounded number rejection;
- PII rejection;
- confidence escalation rejection;
- extra key/autonomous action rejection;
- evaluation release gate;
- model disabled during tests;
- deterministic brief default;
- model-disabled fallback;
- unsupported question;
- bad region;
- drilldown filters;
- proof closure;
- session isolation.

### 22.3 Verification honesty

The above test state comes from committed reports and source inspection.

Before a release, independently rerun:

```powershell
python -m pytest -q
```

with a test database or the repository’s configured in-memory test layer.

Also run:

```powershell
cd frontend
yarn install
yarn build
```

Do not claim a current passing state only from old XML/JSON reports after source
changes.

### 22.4 Test isolation

Tests must:

- force `MODEL_ENABLED=false`;
- never call a model;
- never mutate the shared demo database;
- use a dedicated test database or in-memory store;
- use fresh demo session IDs.

---

## 23. Setup and Reproducibility

### 23.1 README claim versus current repository

`README.md` currently instructs:

```text
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

The `.env.example` files were not present when this handoff was written.

This is a real reproducibility defect.

Create non-secret examples for:

Backend:

```text
MONGO_URL=
DB_NAME=pulse_ai
CORS_ORIGINS=http://localhost:3000
EMERGENT_LLM_KEY=
MODEL_ENABLED=false
MODEL_DAILY_RUN_LIMIT=25
MODEL_MIN_SECONDS_BETWEEN_RUNS=20
MODEL_TIMEOUT_SECONDS=12
MODEL_CACHE_TTL_SECONDS=86400
MODEL_MAX_OUTPUT_TOKENS=700
```

Frontend:

```text
REACT_APP_BACKEND_URL=http://localhost:8001
```

Never place a working secret in an example file.

### 23.2 Package manager

The current project uses Yarn and has a Yarn lockfile in the corrected build
lineage.

Do not casually switch between Yarn and npm.

### 23.3 CRA debt

Create React App / `react-scripts 5.0.1` has known dependency security debt.

The earlier audit observed multiple npm audit findings.

Do not destabilize the competition build by migrating frameworks immediately.

Plan a separate Vite migration after:

- a visual regression baseline;
- route tests;
- API integration tests;
- build comparison.

---

## 24. Known Issues and Open Risks

### P1 — RESOLVED 2026-06-13 (Track A, commit `7f9f2f9`)

1. ~~Missing `backend/.env.example`.~~ Added.
2. ~~Missing `frontend/.env.example`.~~ Added.
3. ~~Navigation still says `Agent Reliability`.~~ Renamed to `Evaluation`.
4. ~~Backend simulation bounds are broader than the correction PRD.~~ Tightened to
   improve_pp 0..15 and avg_realized_value >0..1,000,000.
5. ~~Untracked `.vercel/` directories exist.~~ `.vercel/` now gitignored.

### P2

6. Evidence Drawer Escape behavior was reported as leaving the backdrop mounted
   in an earlier test report. Check current source/browser before assuming it
   remains.
7. Model synthesis latency was reported around 14 seconds, while configured
   timeout behavior and provider latency need live verification.
8. Create React App dependency debt remains.
9. Root image is unrelated repository content.
10. `@app.on_event("startup")` is a deprecated FastAPI lifecycle pattern and can
    later migrate to lifespan.
11. Mongo intervention/proof IDs based on collection counts may need stronger
    concurrency-safe IDs for production.
12. `shared-demo` is only a fallback, not production tenancy.

### Strategic/open

13. Unified Supabase database is proposed, not provisioned.
14. Canonical clinic identity crosswalk — **built v0.1 at demo scope**
    (`docs/unified-database/seed-crosswalk.sql` + `crosswalk.md`). One proven cross-product
    identity (Kamla Nagar: Pulse `DL-KMN-01` = Clove `5129`); 17 canonical clinics, 31 actors,
    14 regions. Scaling to the full 576-clinic Clove master (Master Tracker + KML) is a gated
    scale-up path, not yet done.
15. Pulse-00 canonical export contract — **finalized v0.1** at
    `docs/pulse-00-canonical-contract.md` (journey, metrics, leakage taxonomy, export
    contract, all traced to `engine.py`). Crosswalk is the remaining Track B item.
16. No live connectors exist.
17. No production authentication or RBAC exists.
18. Complete CAC-to-LTV is not implemented.
19. Real design-partner data availability remains to be confirmed.

---

## 25. Unified Database Plan

### 25.1 Proposed schemas

`core`:

- region;
- clinic;
- clinic aliases;
- actors;
- ingest batches;
- evidence;
- canonical events;
- interventions;
- closure proofs;
- cross-product intervention feed.

`pulse`:

- campaigns;
- leads;
- contact attempts;
- appointments;
- revenue;
- leakages.

`reputationos`:

- tickets;
- SLA policies;
- ticket events;
- complaints/reviews/NPS context.

### 25.2 Data doctrine

- append-only events are source truth;
- domain tables are current-state projections;
- every derived claim retains provenance;
- external event time and observed-at time are separate;
- unknown event time may be null;
- never fabricate timestamps;
- no raw PII in the intelligence layer;
- no external writeback in the MVP.

### 25.3 Access

Proposed roles:

- `pulse_app`;
- `reputationos_app`;
- `analytics_ro`.

Use scoped grants and row-level security.

### 25.4 Decisions (approved by Dr. Ishaan, 2026-06-13)

1. **Host:** new dedicated Supabase project (NOT the Dental Lab project) — isolated
   blast radius/billing; a new project is free.
2. **ReputationOS client:** Prisma in introspection mode (`prisma db pull`); schema
   migrations owned by SQL/Supabase, NOT Prisma Migrate. One migration authority for a
   shared two-language DB; Pulse uses generated Python types.
3. **Canonical clinic:** yes — keyed by internal `clinic_uid`; `canonical_code` = Clove/SAP
   (real, 576); Pulse demo codes aliased. Raw SAP codes are an internal join key only and
   must never be rendered on demo/external surfaces.
4. **Environments:** one dedicated project now (all data synthetic); add a separate prod
   project when the first real export/pilot dataset arrives (also the DPDP/residency trigger).

No agent may provision this database merely because the schema exists. Hard prerequisites
remain: Pulse-00 (canonical journey/metrics/leakage/export contract) and the clinic/actor/
region identity crosswalk — both buildable now without provisioning anything.

---

## 26. Competition Demo

### 26.1 Ninety-second script

> Revenue teams do not lack data. They lack a single, trustworthy view of where
> revenue is leaking.
>
> This is Pulse AI, a revenue operations intelligence layer connecting
> marketing leads, CRM activity, telephony, appointments, and revenue outcomes.
>
> Here is the Revenue Cockpit. It reconstructs the journey from lead captured
> to appointment attended and immediately highlights where conversion is
> breaking.
>
> Pulse has detected a contact-rate leakage in the North region. We can see the
> affected cohort, benchmark, accountable owner, and underlying evidence, not
> just a black-box AI score.
>
> The opportunity estimate is deterministic and non-overlapping, so the same
> potential revenue is never counted twice.
>
> Pulse AI then explains why this matters and recommends the next
> human-approved action. The AI cannot invent metrics, cite unseen evidence, or
> execute changes autonomously.
>
> Finally, we assign the intervention, track ownership, and only close it after
> proof is submitted and verified.
>
> Pulse AI turns fragmented revenue data into one operational truth: where
> revenue is leaking, why it is happening, who owns it, and what should happen
> next.

### 26.2 Demo path

1. Revenue Cockpit.
2. North-region leakage.
3. Evidence and affected cohort.
4. Non-overlapping opportunity pool.
5. Deterministic brief.
6. Optional explicit AI synthesis.
7. Assign owner.
8. Proof Required.
9. Claim closure.
10. Separate verification.
11. Evaluation/Data Quality if judges ask about trust.

### 26.3 Do not spend time on

- login;
- settings;
- database administration;
- architecture diagrams unless asked;
- long feature tour;
- generic AI chat.

---

## 27. Expected Competition Q&A

### What problem does Pulse AI solve?

It combines fragmented marketing, CRM, telephony, and appointment signals to
show where the revenue journey is leaking and who should act.

### Is it another CRM?

No. It is an intelligence and accountability layer above existing systems.

### Is the current data real?

No. The competition MVP intentionally uses deterministic synthetic data. A
pilot would begin with approved customer exports.

### What does the AI do?

It explains deterministic leakage findings and recommends evidence-backed,
human-reviewed next actions.

### Can it hallucinate numbers?

Authoritative numbers come from the deterministic engine. Model output must cite
allowlisted metrics and evidence and pass schema, privacy, provenance,
confidence, and numeric validation.

### Does it act autonomously?

No. External writeback is disabled. Recommendations require humans, and closure
requires proof plus verification.

### How is opportunity calculated?

Through a contact, booking, and attendance waterfall using explicit benchmark
assumptions. Opportunity groups do not overlap.

### Is this a forecast?

No. It is a deterministic scenario estimate.

### Who buys it?

Initially multi-location healthcare operators and other lead-driven
organizations with fragmented acquisition and operational systems.

### What is the moat?

The combination of canonical journey reconstruction, evidence-bound leakage,
non-overlapping opportunity, human ownership, and proof-based closure.

### What is next?

A controlled export-based pilot, then approved CRM, ad-platform, telephony, and
appointment integrations.

---

## 28. Commercial/GTM Direction

Original indicative pricing:

- core intelligence: USD 30-50 per user/month;
- simulation add-on: USD 20-30 per user/month.

Do not treat this as validated pricing.

Healthcare pilot direction:

- export-based discovery;
- one region or bounded clinic set;
- clear baseline;
- weekly operational review;
- measured leakage-resolution outcome;
- integration only after value is demonstrated.

The broader product can target:

- B2B SaaS;
- enterprise sales;
- multi-location services;
- healthcare chains;
- high-volume lead operations.

---

## 29. Non-Negotiable Product Boundaries

Do not:

- make AI the source of metric truth;
- add real personal or patient data casually;
- fabricate evidence;
- fabricate timestamps;
- sum related leakage cards;
- permit direct close;
- permit self-verification;
- call a paid model on page load;
- remove model budgets;
- return provider errors to users;
- add autonomous external action;
- promise live integrations that do not exist;
- claim full CAC-to-LTV;
- call offline synthetic evaluation production accuracy;
- collapse Pulse AI and ReputationOS into one undifferentiated UI;
- provision cloud resources without explicit approval;
- delete unrelated user files while doing hygiene;
- commit generated `.vercel`, build, cache, or secret files.

---

## 30. Agent Operating Protocol

Before editing:

1. Read this file.
2. Read `README.md`.
3. Read `memory/PRD.md`.
4. Read the relevant source module.
5. Run:

```powershell
git status --short --branch
git log --oneline -5
git diff --stat
```

6. Preserve user and parallel-agent changes.
7. Identify whether the task is:
   - product correction;
   - competition demo;
   - shared database planning;
   - deployment;
   - connector work.
8. Do not cross those boundaries implicitly.

During implementation:

- keep deterministic calculations pure;
- write tests for economic or accountability changes;
- retain evidence provenance;
- preserve synthetic-data boundary;
- avoid unrelated refactors;
- use explicit error codes;
- keep frontend states responsive and inspectable.

Before completion:

```powershell
git diff --check
python -m pytest -q
cd frontend
yarn build
```

Also perform browser QA for user-facing changes.

Report:

- files changed;
- behavior changed;
- tests/build results;
- risks;
- git status;
- whether any commit, push, deployment, cloud resource, paid model, or real
  data was used.

Delivery is not manager approval.

---

## 31. Immediate Next Actions

### Competition readiness

1. Add missing environment example files.
2. Change the navigation label from `Agent Reliability` to
   `Offline Evaluation` or `Evaluation`.
3. Reconcile backend simulator limits with the intended 0-15pp / bounded-value
   contract.
4. Inspect and clean untracked `.vercel/` directories without committing them.
5. Re-run backend tests and frontend build.
6. Run a timed 90-second browser demo rehearsal.
7. Verify model synthesis is not required for the core demo.

### Product work after competition

8. Finalize Pulse-00 — **DONE v0.1** (`docs/pulse-00-canonical-contract.md`):
   - canonical journey (4-stage funnel ending at Attended; treatment/revenue contextual);
   - metric definitions (exact num/den, traced to `compute_metrics`);
   - leakage taxonomy (L-01..L-08, thresholds, `shared`/`allocation`/`diagnostic` relationships);
   - export contract (entity→`core`/`pulse` table mapping, identity/provenance/privacy rules).
9. Obtain Vikram’s data-source reality:
   - lead exports;
   - campaign spend;
   - CRM stages;
   - call attempts;
   - appointments;
   - revenue/treatment fields;
   - region/clinic/owner mapping.
10. Decide the unified database project and environment structure.
11. Build clinic/actor/region crosswalk before shared-database claims. **DONE v0.1**
    (demo scope) — `docs/unified-database/seed-crosswalk.sql`. Scale to full 576-clinic
    Clove master (Master Tracker + KML) is a separate gated step.
12. Implement database adapters behind unchanged route contracts.
13. Run one controlled export-based design-partner pilot.

---

## 32. Current Git and Delivery Cautions

When this file was written:

- local `main` matched `origin/main` at `b013c41`;
- `backend/.vercel/` and `frontend/.vercel/` were untracked;
- earlier v0.2 implementation was present in committed source;
- unified database documentation was committed;
- no live shared database had been provisioned.

Verify this state again. It will become stale.

Do not assume Emergent auto-generated commit messages describe meaningful
product milestones. Read their diffs.

### 32.1 Live deployment (2026-06-13)

Pulse AI is now deployed live on Vercel via the Vercel CLI (`vercel --prod`),
NOT through a GitHub-connected project. Pushing to `origin/main` therefore does
NOT auto-redeploy; deploys are manual.

- Frontend project `pulse-ai`: `https://pulse-ai-sepia.vercel.app` (CRA build).
- Backend project `pulse-ai-backend`: `https://pulse-ai-backend-nine.vercel.app`
  (FastAPI served by a serverless entrypoint `backend/api/index.py` +
  `backend/vercel.json`).
- Frontend build-time env `REACT_APP_BACKEND_URL` points at the backend URL.

Backend runtime on Vercel:

- No `MONGO_URL`, `EMERGENT_LLM_KEY`, or model key is configured.
- `server.py` now makes `MONGO_URL`/`DB_NAME` optional with an in-memory fallback
  (`interventions`, `proofs`, `model_budget`, `model_cache`; `$set`/`$inc`/upsert/
  `delete_many`). It runs deterministic-only. Read flows (`meta`, `cockpit`,
  `opportunity`, `leakages`, `journeys`, `evaluation`, `model-budget`,
  `interventions`) and the deterministic `POST /api/brief` are verified live (200);
  sim bounds enforced (10pp→200, 20pp→422).
- Mutable state (interventions, proofs, session/model budgets) is NOT durable
  across serverless cold starts in this configuration. Set `MONGO_URL` for durable,
  session-isolated persistence.

Reproducibility (resolved 2026-06-13, Track A):

- The live site now runs the corrected v0.2 (CP-04..08) build and IS reproducible
  from `origin/main` at `7f9f2f9`. The serverless entrypoint (`backend/api/index.py`
  + `backend/vercel.json`), the in-memory fallback, and the `api.js` HTML-response
  guard are committed.
- `emergentintegrations` has been **removed** (ADR-0006), so the old "re-comment
  the pin before redeploying" hazard no longer applies. The model path is decoupled
  behind a neutral `_complete()` seam in `briefing.py`; it now uses Vertex AI
  Gemini (ADR-0007), enabled by setting `LLM_API_KEY`. NOTE: the Emergent integration must be
  disconnected on the Emergent platform itself so its auto-commit bot stops pushing
  to `main` — deleting `.emergent/` in-repo does not do that. Until disconnected,
  keep reading the bot's diffs (§32, above).

No live shared database was provisioned. This deployment is a synthetic demo.

---

## 33. Closing Doctrine

Pulse AI should feel intelligent because it can prove what it says.

The product sequence is:

```text
Source
  -> Deterministic fact
  -> Evidence
  -> Leakage
  -> Non-overlapping opportunity
  -> Human-owned intervention
  -> Proof
  -> Verification
  -> Executive story
```

AI sits inside that sequence as a bounded interpreter.

It does not replace the sequence.

The product is not a dashboard that tells impressive stories about uncertain
numbers. It is an accountability engine that allows a leader to move from a
number to its evidence, from evidence to an owner, and from an owner to proof.

That is the heart of Pulse AI. Preserve it.
