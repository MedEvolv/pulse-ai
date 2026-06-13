# Pulse AI — Product Memory

## Original Problem Statement
Build Pulse AI per attached PRD (Emergent Hackathon MVP v0.1): a healthcare Revenue Operations
intelligence app that identifies why paid healthcare leads fail to become attended appointments
across regions/clinics. User said "mobile app"; PRD specifies a responsive web cockpit (works at
1440x900 + 390x844). Built as a responsive web app per PRD.

## Architecture
- **Backend (FastAPI, /app/backend)**
  - `engine.py` — SINGLE SOURCE OF TRUTH. Deterministic synthetic data (fixed seed, no runtime
    randomness), metric selectors, leakage rules + severity scoring, evidence index.
  - `briefing.py` — Regional Leakage Briefing Agent. Claude Sonnet 4.6 via `emergentintegrations`
    (EMERGENT_LLM_KEY) with schema validation + privacy/evidence guards. Deterministic template
    fallback always works without a model key. ~20s model latency, instant fallback.
  - `evaluation.py` — 10 deterministic benchmark fixtures + weighted scoring (currently 100%, 10/10).
  - `server.py` — all `/api` routes; interventions persisted in MongoDB (seeded on startup).
- **Frontend (React CRA + Tailwind, /app/frontend)** — routes: /cockpit, /journeys, /journeys/:id,
  /leakages, /leakages/:id, /simulation, /data-quality, /evaluation. Shared FilterContext (region).
  Operational/dense design per PRD palette; Inter font.

## Designed Demo Pattern (deterministic)
- North = at-risk: contact rate ~48%, median first-contact 266m, show rate ~53%, CPA ~₹18.3K,
  3 high-severity leakages (low_contact_rate, slow_first_contact, high_cost_per_attended) + Rohini
  (DL-RHN-02) no-show/concentration. West = healthy. South = booking-stage drop.

## Implemented (2026-06-13)
- Cockpit (health strip + prior deltas, funnel, AI brief panel + search-first, top leakage, regional comparison) ✓
- Search-first brief with 5 suggested questions, evidence chips → evidence drawer ✓
- Leakage queue + detail (formula, severity breakdown, affected leads, human intervention flow w/ persistence) ✓
- Journeys explorer + filters + pseudonymous evidence timeline ✓
- Deterministic scenario simulator ✓
- Data Quality readiness + 6 source cards ✓
- Agent Reliability evaluation page (ring, dimensions, 10 fixtures) ✓
- Responsive desktop + mobile bottom nav; hard-refresh safe on all routes ✓
- Tested: 20/20 backend, 100% frontend flows (iteration_1.json) ✓

## Backlog / Next
- P1: Stream the AI brief token-by-token (SSE) to mask ~20s latency, or default to deterministic
  with a "Run AI brief" toggle for a snappier demo.
- P2: CSV upload of export-shaped data (PRD "Could Pass").
- P2: Treatment/revenue stage depth + complaint/NPS overlay.
- P2: Styled dropdown for region selector (currently native <select>).
- Deployment: single Emergent deployment, run pre-deployment health check before judging.

## Notes
- No authentication (PRD out of scope). Synthetic data only; no PII in journeys.
- EMERGENT_LLM_KEY in backend/.env; app fully functional via deterministic fallback without it.
