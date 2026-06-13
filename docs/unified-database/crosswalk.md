# Identity Crosswalk — ReputationOS + Pulse AI

**Status:** v0.1 · 2026-06-14 · seed: [`seed-crosswalk.sql`](seed-crosswalk.sql)

This is the table that makes "shared database" true. It maps each product's external
identifiers (clinic codes, owners, regions) onto one canonical set in `core.*`, satisfying
the export contract in [`../pulse-00-canonical-contract.md`](../pulse-00-canonical-contract.md) §5.2.
Build it before any shared-data claim; provisioning stays gated ([README §7](README.md)).

## Sources (what actually exists today)

| Product | Source | Clinics | People |
|---|---|---|---|
| Pulse AI | `backend/engine.py` `CLINICS` / `OWNERS` | 12 synthetic | 5 owners |
| ReputationOS | `src/features/reputationos/domain/demo-data.ts` | 6 real Clove | heads, ops, agents, managers, escalation |

No KML / Master Tracker was parsed for v0.1 — lat/lng are NULL (honesty rule: absent
data stays absent). The 576-clinic Clove master is the documented scale-up path below.

## The reconciliation (and its honest limits)

- **One proven cross-product identity:** **Kamla Nagar** — Pulse `DL-KMN-01` = Clove `5129`.
  It is the only canonical clinic carrying aliases from *both* products. This single row is
  the demonstrable proof that the two products can share data.
- **Thane is deliberately NOT merged.** Pulse `MH-THN-03` ("Thane") is a generic synthetic
  locality; Clove `7102`/`7103` are two specific Thane addresses. Merging them would invent
  an identity the data doesn't support → three distinct canonical rows.
- **Actor sets are disjoint.** Watch the near-name collisions that are *different people*:
  repos `Priya Sharma` ≠ Pulse `Priya Deshmukh`; repos `Rohan Sethi` ≠ Pulse `Rohan Iyer`.
  Never auto-merge on first name.
- **`canonical_code` = the real Clove id where one exists** (decision §7.3). It is an
  internal join key only — never rendered on demo/external surfaces. Pulse-only synthetic
  clinics keep their Pulse code as `canonical_code` until a real Clove id is assigned.

## Region hierarchy (one tree, both granularities)

Pulse's 3 coarse bands sit *above* ReputationOS's region/sub_region:

```
REG-NORTH (band) → North India → {Delhi NCR, Punjab}
REG-WEST  (band) → Mumbai           → {Mumbai}
                 → South West India  → {Gujarat}
REG-SOUTH (band) → South East India  → {Telangana}
                 → South India       → {Karnataka}   (Pulse south clinics)
```

Pulse reads at the band; ReputationOS reads at the leaf. Same tree.

## Expected seed counts (v0.1)

`region` 14 · `clinic` 17 · `clinic_alias` 24 · `actor` 31. Verification queries are at the
foot of `seed-crosswalk.sql`.

## Scale-up path (gated, not v0.1)

To go from the 6 demo clinics to the full **576-clinic Clove estate**:

1. Ingest the **Clove Master Tracker** (`Master Tracker.xlsx`, in the vault) → one
   `core.clinic` row per real clinic, `canonical_code` = Clove id, plus `core.clinic_alias`
   `(clove, <id>)`.
2. Join the **geocoded/KML** source to populate `latitude`/`longitude` (currently NULL).
3. Re-point each ReputationOS demo clinic's alias at its master row (ids already align —
   they use Clove ids today).
4. Map any *new* real clinics Pulse begins using to their Clove master row via
   `core.clinic_alias (pulse, <code>)`.

This requires reading private Clove data and is a separate, explicitly green-lit step — it
does **not** run as part of demo seeding.
