# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root, or
- **`CONTEXT-MAP.md`** at the repo root if it exists — it points at one `CONTEXT.md` per context. Read each one relevant to the topic.
- **`docs/adr/`** — read ADRs that touch the area you're about to work in.

This is a **single-context** repo: one `CONTEXT.md` + `docs/adr/` at the root. Neither exists
yet — proceed silently if absent. `/grill-with-docs` creates them lazily when terms or
decisions actually get resolved.

In addition to `CONTEXT.md`, this repo already keeps a rich canonical record — read these too:

- **`AGENT.md`** — product intent, architecture, truth boundaries, known risks, decisions.
- **`docs/pulse-00-canonical-contract.md`** — the canonical revenue contract (funnel,
  metric definitions, leakage taxonomy, export contract). Treat its frozen terms as the
  domain glossary: `lead`, `contact`, `booking`, `show`, `opportunity group`
  (`shared`/`allocation`/`diagnostic`), `leakage`, `intervention`, `evidence`.
- **`docs/unified-database/`** — schema + crosswalk for the shared ReputationOS/Pulse data.

## File structure

Single-context repo:

```
/
├── CONTEXT.md            (created lazily by /grill-with-docs)
├── AGENT.md              (canonical handoff — already exists)
├── docs/
│   ├── adr/              (created lazily)
│   ├── pulse-00-canonical-contract.md
│   └── unified-database/
└── backend/ , frontend/
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md` — and, until that exists, as defined in `docs/pulse-00-canonical-contract.md`. Don't drift to synonyms the contract explicitly avoids (e.g. don't call the opportunity waterfall a "forecast"; don't treat treatment/revenue as part of the primary funnel).

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/grill-with-docs`).

## Flag ADR conflicts

If your output contradicts an existing ADR — or a frozen decision in `AGENT.md` /
`pulse-00` / the unified-database README — surface it explicitly rather than silently
overriding:

> _Contradicts pulse-00 §5.4 (frozen stage_key values) — but worth reopening because…_
