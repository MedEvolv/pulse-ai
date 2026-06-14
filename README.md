# Pulse AI — Revenue Operations Intelligence (Hackathon MVP)

Pulse AI is a synthetic-data healthcare Revenue Operations cockpit. It explains **why paid
healthcare leads fail to become attended appointments** across regions and clinics using a
deterministic metrics + leakage engine, an evidence-bound AI briefing agent (with a deterministic
fallback that always works), human-owned interventions with proof-based closure, a scenario
simulator, and an honest offline evaluation harness.

> Synthetic data only. No real patient or lead data. No autonomous external action.

## Tech stack
- **Backend:** FastAPI + Motor (MongoDB), Python.
- **Frontend:** React (CRA) + Tailwind CSS, React Router.
- **Model:** Claude Sonnet 4.6 via the Anthropic API (direct) — **off by default**, explicit and
  budget-limited. The product is fully usable without any model. (Emergent removed — ADR-0006;
  the direct-Anthropic path is a tracked follow-up, deterministic until wired.)

## Project layout
```
backend/
  engine.py            # single source of truth: data, metrics, opportunity waterfall, leakage, evidence
  briefing.py          # deterministic brief + validated model synthesis
  brief_validation.py  # strict Pydantic + provenance/privacy/numeric/confidence validators
  model_budget.py      # daily limit, cooldown, cache, bounded tokens (server-side)
  evaluation.py        # 20 adversarial offline fixtures through production validators
  server.py            # FastAPI routes (all under /api)
  tests/               # offline tests (isolated DB, no model calls)
frontend/src/
  pages/  components/  lib/  context/
```

## Run locally
The app is self-contained — it runs on the in-memory adapter with no external services
(set `MONGO_URL` only if you want durable Mongo-backed state). Locally:

```bash
# Optional: set MONGO_URL for durable state; omit to use the in-memory adapter
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env            # then fill values
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Frontend (uses yarn; do not switch to npm)
cd frontend
cp .env.example .env            # set REACT_APP_BACKEND_URL
yarn install
yarn start                      # http://localhost:3000
```

## Tests (offline, no model, isolated DB)
```bash
cd backend
DB_NAME_TEST=pulse_ai_test python -m pytest -q --junitxml=../test_reports/pytest/pulse_api.xml
```
Tests refuse to run against the demo database and never call a model provider
(`MODEL_ENABLED=false` is forced in `tests/conftest.py`).

## Frontend build
```bash
cd frontend && yarn build
```

## Key guarantees
- **Economic truth:** stage opportunity is a non-overlapping waterfall; only unique stage pools are
  additive; high cost-per-attended is diagnostic and creates no recovery pool.
- **AI safety:** every model finding must cite an allowlisted metric ID + evidence ID; output is
  validated for schema, provenance, privacy, ungrounded numbers, and confidence escalation. Any
  failure discards the model output and uses the deterministic brief.
- **Accountability:** closure follows `Proof Required → Closure Claimed → Closed` with a structured
  proof record and a **separate** verification action (no self-close).
- **Spend control:** deterministic by default; model runs are explicit, daily-limited, cooled-down,
  cached, timed out, and token-bounded.
- **Isolation:** each browser gets an anonymous demo session; changes never affect other users.

## Versions
data `data-1.0.0` · rules `rules-2.0.0` · prompt `brief-2.0.0` · eval `eval-2.0.0`
