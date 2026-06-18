# Pulse AI

The Revenue Operations intelligence layer for a dental-clinic network: it surfaces where
acquisition revenue leaks between lead and attended appointment, and drives evidence-backed
interventions to recover it.

This is the **glossary** — canonical terms and the words to avoid. Implementation lives in
code; revenue-domain terms (funnel stages, metrics, leakage taxonomy, opportunity groups)
are defined authoritatively in `docs/pulse-00-canonical-contract.md` and are not duplicated
here. This file captures terms resolved in grilling sessions that aren't already pinned there.

## Language

### Storage

**Deterministic catalogue**:
The read-only dataset `engine.py` generates from a fixed seed — leads, contact attempts,
appointments, revenue, reputation events, leakages, opportunity groups, and evidence. It is
identical on every run and is the single source of truth for those facts. It is *never*
persisted to the database.
_Avoid_: "the data", "seed data", "the dataset" (ambiguous with the mutable fabric).

**Mutable fabric**:
The user-created, changeable state that *does* persist: interventions, closure proofs, and
model-budget/cache. This is the only thing the database backs, and the only thing shared
with ReputationOS through the `core` schema. It is the alignment keystone.
_Avoid_: "the records", "the state" (say which: catalogue or fabric).

**Adapter**:
The storage implementation selected at runtime by environment — in-memory (default),
Mongo (`MONGO_URL`), or Postgres (`DATABASE_URL`). An adapter backs only the mutable
fabric; it never serves the deterministic catalogue.
_Avoid_: "the backend" (overloaded with the FastAPI service), "the store".

**Cited evidence**:
The subset of catalogue evidence that gets persisted into `core.evidence` — and only that
subset — because a closure proof references it. The rest of the catalogue's evidence is
never written to the database.
_Avoid_: "the evidence" (unqualified — most catalogue evidence is never persisted).
<!-- PULSE AI V1.0 GLOSSARY ADDENDUM -->
<!-- This is appended to the existing CONTEXT.md in C:\ArchLife-Systems\pulse-ai\ -->
<!-- Date: 2026-06-17 -->
<!-- Source: grill-with-docs session -->

---

# v1.0 Glossary Addendum (2026-06-17)

The Pulse-00 CONTEXT.md (above) defines the deterministic catalogue, mutable fabric, adapter, and cited evidence terms. The v1.0 glossary (locked 2026-06-17) extends Pulse-00 with 22 v1.0 terms. **Pulse-00 terms are preserved. v1.0 terms are layered on top.**

## Language (v1.0 extensions)

**Pulse AI**:
The product family â€” the umbrella under which all deployments, all sectors, and all company-specific configurations live. Includes RevOpsOS, the sector governance layer, the company knowledge layer, and any industry-specific modules (ReputationOS, future sector modules).
_Avoid_: the platform, the system, Pulse, the Pulse product

**RevOpsOS**:
The universal engine's public-facing surface name. The sector-independent compute + identity + AI evidence + intervention fabric. One engine, six sector-shaped governance profiles, N company-shaped knowledge layers.
_Avoid_: the engine, the universal engine, the RevOps engine

**ReputationOS**:
The industry-vertical module under Pulse AI that holds the healthcare-specific artefacts (the Kamla Nagar crosswalk, the hospital simulator, the clinical event escalation patterns). It is one vertical module of Pulse AI, NOT the umbrella.
_Avoid_: the parent product, the platform, the brand

**Sector**:
One of the six industries Pulse AI supports in v1: Healthcare, Retail, SaaS (mid-market), Automotive & Mobility, Hospitality, Financial Services. Each sector has its own governance profile (rulesets, protocols, policies, cadences) and its own AI evidence templates. Sectors are chosen by the operator at the demo init.
_Avoid_: vertical, industry, domain, niche

**Company**:
A single multi-location operator that has its own deployment of Pulse AI. Each company has its own RAG + PKM knowledge layer seeded with its own institutional memory (SOPs, playbooks, closure proofs, exception logs).
_Avoid_: customer, client, account, tenant, organization

**Operator**:
The named person at the company who uses Pulse AI day-to-day. The clerk, the clinic manager, the store manager, the CSM, the RM, the dealer principal. The owner of the closure proof, the named escalator, the human actor.
_Avoid_: user, customer, admin, employee

**Customer**:
The end entity the company serves â€” a patient, a shopper, a SaaS subscriber, a vehicle owner, a guest, a private banking client. Pseudonymous in the engine, hash-keyed, never PII in the AI narrative. The cycle's anchor.
_Avoid_: patient (use "customer" universally), user, end-user

**Closure proof**:
The signed record that an intervention was completed. The named operator (clinic manager, store GM, CSM, RM) signs off, with attribution + visit log + named follow-up. The institutional memory unit. The thing the company knowledge layer cites.
_Avoid_: completion record, audit trail, sign-off, ticket closure

**Cohort**:
A named customer segment in the engine. The Critical Few (Pareto) cohorts are surfaced in the AI narrative. Cohorts are sector-shaped and company-shaped.
_Avoid_: segment, audience, persona, list

**Sector knowledge**:
The shared knowledge of a sector â€” rulesets, protocols, policies, cadences. Lives in the sector governance profile (6 of them in v1). Updated rarely, when the sector shifts. Read-only from the company's perspective.
_Avoid_: industry knowledge, vertical knowledge, sector data, sector context

**Company knowledge (PKM)**:
The per-deployment institutional memory of one company. SOPs, playbooks, closure proofs, exception logs, named people, named interventions. Grows every day the company uses Pulse AI. The institutional moat.
_Avoid_: tenant data, customer data, account data, deployment data

**Customer knowledge**:
The per-person, anonymous-pseudonymous knowledge of one customer in the engine. Visit history, recall cadence, complaint patterns, named-owner handoffs, the engine's named risk and opportunity per customer. Hash-keyed.
_Avoid_: customer data, customer record, user profile, customer profile

**Cycle stages (5 universal)**:
The five stages of the flywheel â€” abstract: Stage 1, Stage 2, Stage 3, Stage 4, Stage 5. Each sector's governance profile gives them sector-specific names. One computation per stage, six sector-specific naming overlays.
_Avoid_: funnel, pipeline, lifecycle stages, journey

**LTV:CAC band**:
The headline LTV:CAC ratio with three reference bands: 2:1 baseline (operational floor), 3:1 target (healthy growth), 4:1 stretch (category-creator). Bands are company-level. Drill-down gives the LTV:CAC at each of the 5 cycle stages, per cohort, per location, per intervention.
_Avoid_: LTV/CAC ratio, LTV-CAC, lifetime value ratio, payback multiple

**Binding constraint**:
The single cycle stage that, if improved, would move the headline LTV:CAC by the largest delta. Computed via Goldratt's Theory of Constraints applied to the 5 cycle stages.
_Avoid_: weakest link, bottleneck, weakest stage, leverage point

**AI narrative**:
The text the engine produces for an operator â€” typically 1-3 sentences with a cite-able evidence format: 'Reference: <doc-name>, last reviewed <date> + closure proof from <date> + named owner <person>.' The narrative is grounded in evidence (sector knowledge, company knowledge, customer knowledge), not generated from a model's training data. The narrative is loss-framed by default (Kaufman's Loss Aversion), uses Conservation of Energy language ('single move' not 'multi-pronged strategy'), and surfaces the Critical Few + Constraint. The provenance lineage is visible by default.
_Avoid_: AI output, AI response, generated text, recommendation

**Provenance lineage**:
The visible evidence chain for every AI narrative â€” operator query â†’ engine computation â†’ sector knowledge + company knowledge + customer knowledge â†’ individual source document. Timestamps at each step. The chain is rendered by default (not hidden behind a 'show reasoning' button).
_Avoid_: audit trail, evidence trail, citation chain, reasoning trace

**Sector depth (Friday 2026-06-20)**:
The shipping depth per sector for the v1.0 Friday demo. Three sectors ship full (Healthcare, Retail, SaaS). Three sectors ship stub (Hospitality, Automotive & Mobility, Financial Services). The depth split is a v1.1 commitment, not a hidden weakness.
_Avoid_: lite, basic, MVP, demo-only

**Friday demo flow (live sector switching)**:
The Friday 2026-06-20 mentor pitch flow. 8 steps, 30-45 min, with live sector switching as the load-bearing moment.
_Avoid_: the demo, the pitch, the run-of-show

**PKM shape (append-only event spine + snapshot projections)**:
The company knowledge layer's two-tier storage. The append-only event spine is the source of truth. The snapshot projections are the operator-queryable current state. The two reconcile periodically.
_Avoid_: audit log, change log, version history

**Operator query (pre-canned library)**:
The operator-facing "Ask [Company]:" surface. A pre-canned library of ~30 questions per sector (3-5 per cycle stage). The operator picks one, the engine computes, the AI narrates with cite-able evidence. No free-text input in v1.
_Avoid_: search box, free-text query, AI assistant, chatbot

**Multi-sector (v1 = one company, one sector; v2.0 = multi-sector)**:
The deployment model. In v1, one company = one sector. Cross-sector expansion is a NEW Pulse AI deployment with a NEW company PKM.
_Avoid_: multi-tenant, multi-vertical, cross-sector

**RevOpsOS surfacing (engine invisible to operator)**:
The brand-architecture decision. RevOpsOS is the universal engine, branded in technical docs + the sector governance panel. The operator never types 'RevOpsOS'; they type 'Pulse AI.' RevOpsOS is for builders, architects, and the sector governance panel; Pulse AI is for operators.
_Avoid_: surface the engine, expose the engine, brand the engine

**Demo data (realistic fictional companies across all 6 sectors)**:
The public demo data shape. All 6 sectors use realistic fictional companies â€” no real brand names. Healthcare is a generic 'multi-location dental chain.' The Clove Dental reference is preserved for the PRIVATE Amar pitch (mentor, not public), NOT in the public demo.
_Avoid_: real companies, public benchmarks, named accounts

**ArchLife**:
The owner of Pulse AI / RevOpsOS â€” the brand, the IP, the code, the deployments, the company knowledge, the sector research. The product's public surface attribution is 'A product of ArchLife' in the flywheel view footer, the sector governance panel, the brief, the .docx, and the closure proof artefacts. Vikram sir is the customer, the mentor, and the public-facing advocate. He is not the owner.
_Avoid_: the company, the vendor, the builder

**Hosting (pulse-ai.archlife.in)**:
The primary deployment domain. pulse-ai.archlife.in is the umbrella subdomain. Company-specific deployments sit inside it as sub-paths. Never hosted on a vendor's primary domain.
_Avoid_: Vercel preview URL, custom domain (not under archlife.in), shared hosting

**Vikram sir's role (customer + mentor + public advocate, NOT owner)**:
The doctrinal clarification. Vikram is the Clove Dental CEO, the customer (pilot), the mentor (Amar pitch), and the public-facing advocate. He is NOT the owner. The fix for the attribution concern is not to correct Vikram's framing (that would be confrontational) but to make the product artefacts so unambiguous that the takeaway is corrected implicitly.
_Avoid_: the builder, the owner, the founder
