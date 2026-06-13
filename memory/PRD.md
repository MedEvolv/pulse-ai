# Pulse AI — Product Memory

## Original Problem Statement
Pulse AI (Emergent Hackathon): synthetic-data healthcare RevOps cockpit explaining why paid leads
fail to become attended appointments. v0.1 built the responsive web cockpit. **v0.2 Correction Pack**
patched it (no regeneration) to fix five foundational issues + lineage/session/drilldown/validation/hygiene.

## Architecture (v0.2)
- **engine.py** — single source of truth: deterministic data, metric selectors, **non-overlapping
  opportunity waterfall**, **cohort-faithful aggregate metric evidence (MEV)**, leakage rules with
  `opportunity_relationship` (shared|allocation|diagnostic) + `is_additive_in_summary=false`, severity.
- **brief_validation.py** — strict Pydantic BriefOutput (extra=forbid) + provenance/privacy/numeric/
  confidence validators → reason codes.
- **briefing.py** — deterministic brief (default) + validated model synthesis (Claude Sonnet 4.6).
- **model_budget.py** — Mongo-backed daily limit / cooldown / cache / timeout / bounded tokens; fail-closed.
- **evaluation.py** — 20 adversarial offline fixtures through production validators; "Offline Evaluation Score".
- **server.py** — /api routes; session-scoped interventions (X-Demo-Session-ID); proof-based closure
  state machine; input validation; CORS credentials disabled.
- **frontend** — BriefPanel (deterministic default + explicit "Run AI synthesis" + budget), Cockpit
  (non-overlapping Recovery Opportunity panel, funnel→attended + partial context), LeakageDetail
  (proof workflow), Journeys (URL drilldown), Evaluation, Layout (reset-my-demo).

## Five corrections (v0.2)
1. **Economic truth (CP-01):** stage waterfall; only unique stage pools additive; clinic = capped
   allocation; high cost = diagnostic (₹0 pool). North before: 6 alert cards each reused ₹1.225L →
   naive overlap ₹7.175L. After: 3 unique pools = Contact ₹2.625L(15) + Booking ₹0.70L(4) +
   Show ₹2.45L(14) = **33 appts / ₹5.775L**; waterfall telescopes to benchmark attendance delta.
2. **AI validation (CP-02):** every finding cites allowlisted metric+evidence IDs; schema/provenance/
   privacy/numeric/confidence rejection → deterministic fallback with reason code.
3. **Honest evaluation (CP-03):** 20 fixtures inject real faults through production validators; no
   hardcoded scores; renamed "Offline Evaluation Score" (synthetic/offline).
4. **Model budget (CP-04):** deterministic default; explicit Run AI synthesis; daily limit/cooldown/
   cache/timeout/bounded tokens; bounded reason codes (no raw provider errors).
5. **Proof closure (CP-05):** Proof Required → Closure Claimed → Closed; structured proof record +
   separate verification action; no direct close.
Plus CP-06 evidence lineage (MEV), CP-07 anonymous session isolation + validation + CORS,
CP-08 URL drilldown cohorts, CP-09 repo hygiene + offline isolated tests.

## Test / build status (2026-06-13)
- Offline pytest: **24 passed** (isolated DB pulse_ai_test, MODEL_ENABLED=false, no model calls).
- Frontend `yarn build`: **success**.
- Testing agent E2E: 100% backend + listed frontend flows. Fixed: EvidenceDrawer Esc-close.
- Versions: data-1.0.0 · rules-2.0.0 · prompt-2.0.0 · eval-2.0.0.

## Known limitations / backlog
- AI synthesis latency ~14s (Sonnet); timeout bound 20s with graceful fallback.
- Lockfile: project uses **yarn** (yarn.lock); CP referenced npm — documented in README, kept yarn.
- Root file `two face dialectics.jpg` (1.8MB, unrelated) tracked since baseline — flagged for removal.
- Git: platform auto-checkpoints each step; no manual commit/push/deploy performed.
