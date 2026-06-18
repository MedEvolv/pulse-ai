---
name: pulse-ai-v1-doctrine
description: Pulse AI v1.0 doctrine — flywheel over funnel, sector-shaped governance, RAG + PKM as the institutional moat. The substrate Pulse-00 builds on. Read first before any v1.0 work.
risk: none
source: synthesized from the 2026-06-17 grill-with-docs session (Vikram 12:26 PM call + Perplexity deep research + 6 sector research files + Kaufman mental models)
date_added: 2026-06-17
tags: [pulse-ai, doctrine, v1, flywheel, sector-agnostic, rag-pkm, archlife]
---

# SKILL.md — Pulse AI v1.0 doctrine

This is the **canonical skill for any agent working on Pulse AI v1.0**. Read this first. The doctrine is locked. The 6 ADRs are decisions, not options. The glossary is the contract.

## The v1.0 doctrine in 5 lines

1. **The engine is one** — RevOpsOS, a universal cycle engine with 5 abstract stages (Stage 1-5).
2. **The governance is six** — sector-shaped profiles (rulesets, protocols, policies, cadences) per sector. YAML config, not code. To add a 7th sector, write one YAML file.
3. **The PKM is per-company** — append-only event spine + snapshot projections. Three knowledge layers: sector (shared), company (per-deployment), customer (per-person, anonymous).
4. **The data is real public Kaggle data + company transactional history + intervention closure proofs.** 5 sectors use Kaggle; Healthcare uses synthetic data shaped like a multi-location dental chain.
5. **The AI narrates, citing the company's own institutional memory.** Every narrative has a cite-able reference + named-owner handoff + provenance lineage visible by default.

## The 14 grill decisions (locked)

1. **Brand architecture:** Pulse AI = product family, RevOpsOS = engine surface name, ReputationOS = healthcare module.
2. **Cycle stages:** 5 universal abstract stages, sector-specific names per governance.
3. **Knowledge layers:** Three (sector / company / customer).
4. **LTV:CAC metric:** Full cohort (company + 5 stage + per-cohort + per-location + per-intervention). Bands: 2:1 baseline, 3:1 target, 4:1 stretch.
5. **Entry point:** Flywheel diagram opens, LTV:CAC in the center.
6. **AI evidence format:** Reference + named-owner handoff. Confidence scores are v2.0.
7. **Sector depth (Friday 2026-06-20):** 3 full (Healthcare, Retail, SaaS) + 3 stub (Hospitality, Automotive, Financial Services).
8. **Friday demo flow:** 8 steps, live sector switching as the load-bearing moment.
9. **PKM shape:** Append-only event spine + snapshot projections.
10. **Operator query:** Pre-canned library, no free-text v1.
11. **Multi-sector:** v1 = one company one sector, v2.0 = multi-sector.
12. **RevOpsOS surfacing:** Engine invisible to operator.
13. **Demo data:** Realistic fictional companies, no Clove in public demo.
14. **Provenance lineage:** Visible by default, with timestamps.

## The 6 ADRs (in docs/adr/)

- **0001** — Flywheel over funnel as the universal cycle shape
- **0002** — Industry-agnostic public surface, sector-shaped governance layer
- **0003** — Per-company RAG + PKM as the institutional moat
- **0004** — Provenance lineage visible by default in every AI narrative
- **0005** — Friday 2026-06-20: 3 sectors full + 3 sectors stub (engineering-honest path)
- **0006** — ArchLife ownership and hosting (pulse-ai.archlife.in)

## The 22 glossary terms (in CONTEXT.md)

Pulse AI, RevOpsOS, ReputationOS, Sector, Company, Operator, Customer, Closure proof, Cohort, Sector knowledge, Company knowledge (PKM), Customer knowledge, Cycle stages (5 universal), LTV:CAC band, Binding constraint, AI narrative, Provenance lineage, Sector depth (Friday 2026-06-20), Friday demo flow (live sector switching), PKM shape, Operator query (pre-canned library), Multi-sector, RevOpsOS surfacing, Demo data, ArchLife, Hosting (pulse-ai.archlife.in), Vikram sir's role.

## The 4 specs (in the vault)

- spec--universal-engine-sector-governance-2026-06-17.md
- spec--rag-pkm-company-knowledge-2026-06-17.md
- spec--sector-toggle-demo-init-2026-06-17.md
- spec--data-acquisition-kaggle-2026-06-17.md

## The 6 sector research files

- Healthcare (10,500 words)
- Retail (9,890 words)
- SaaS — mid-market (10,565 words)
- Hospitality (12,454 words)
- Financial Services (9,973 words)
- Automotive & Mobility (2,434 words INCOMPLETE — re-running via Packet 12)

## The 5 mental models (Kaufman deep dive)

- **Five Parts of Every Business** = the flywheel
- **Iron Law of the Market** = the gate for industry-agnostic
- **LTV:CAC** = the headline number (with bands)
- **Reactivation** = the second product screen
- **Constraint (Goldratt)** = the binding constraint
- Plus: Conservation of Energy, Loss Aversion, Critical Few (Pareto), Caveman Syndrome

## The 5 build packets for this repo (in parallel today)

- **Packet 01** — sector toggle + dataset coercion engine
- **Packet 02** — universal engine refactor
- **Packet 03** — RAG stack
- **Packet 05** — seed PKM data per company
- **Packet 06** — Firecrawl sector protocols

## Hosting & ownership

- **Hosting:** pulse-ai.archlife.in
- **Owner:** ArchLife
- **Attribution:** "A product of ArchLife" footer in every screen
- **Vikram sir's role:** customer (Clove Dental pilot), mentor (Amar pitch Friday 2026-06-20), public-facing advocate. NOT the owner.

## The Pulse-00 substrate (preserved)

The v1.0 doctrine builds on the Pulse-00 substrate:
- **Pulse-00 engine:** the deterministic compute layer, sector-independent (5 cycle stages now)
- **Hospital simulator + Kamla Nagar crosswalk:** the healthcare deep demo
- **Unified DB schema:** the canonical data shape
- **Closure proof + named-owner handoff:** the institutional memory unit
- **AI briefing + deterministic fallback:** the AI evidence layer
- **Accountability state machine:** Proof Required → Closure Claimed → Closed

**Pulse-00 is the substrate. The v1.0 doctrine is the framing. Both coexist.** Pulse-00 lives in backend/ + frontend/. The v1.0 doctrine lives in CONTEXT.md, AGENT.md, docs/adr/, and this SKILL.md. The Friday demo is the v1.0 framing on the Pulse-00 substrate.

## What to do on a v1.0 task

1. **Read this SKILL.md first** (5 min).
2. **Read CONTEXT.md** for the 22 glossary terms (5 min).
3. **Read the relevant ADR(s)** in docs/adr/ (5 min each).
4. **Read the relevant spec** in the vault (10 min each).
5. **Read the relevant sector research file** for the sector you're working in (10 min each).
6. **Check the goal prompt** in _GOAL_PROMPTS--opus-4-8.md if your task is a build packet.
7. **Then start work** — the doctrine is locked, the glossary is canonical, the ADRs are decisions.

## The doctrine (one more time)

> *The engine is one. The governance is six. The PKM is per-company. The data is real public data + company transactional history + intervention closure proofs. The AI narrates, citing the company's own institutional memory. The operator queries, "Ask [Company]:". The flywheel is a cycle, not a funnel. LTV:CAC is the headline number. The health of your company is equal to the happiness of your customer. To add a 7th sector, you write one YAML file. To add a 7th company, you ingest its documents. The moat is the PKM, because the engine is commodity, the governance is sector-shaped wisdom, and the PKM is the company's institutional memory that grows over time. **Hosted at pulse-ai.archlife.in. A product of ArchLife.***

**A product of ArchLife. Hosted at pulse-ai.archlife.in.**
