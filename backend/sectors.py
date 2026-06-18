"""
Pulse AI - Sector coercion + registry layer (RevOpsOS governance config).

This is the v1.0 sector layer on the Pulse-00 substrate. The engine is sector-blind
(see CONTEXT.md glossary): a per-sector YAML governance profile in `sectors/` shapes the
universal cycle. This module loads those profiles and *coerces* every sector into one
canonical data shape -- the same flywheel (5 universal cycle stages), the same LTV:CAC
band, sector-shaped labels and deterministic seeds.

Doctrine:
  * One engine, six governance profiles. To add a 7th sector, drop in one YAML file.
  * 5 universal cycle stages: spend -> revenue -> retention -> expansion -> referral,
    named per sector via the profile's `stage_labels`.
  * LTV:CAC band: 2:1 baseline, 3:1 target, 4:1 stretch (per-sector defaults in the YAML).
  * Per-company + per-stage + per-cohort + per-location LTV:CAC, deterministic (no runtime
    randomness -- seeded via hashlib, matching the engine's deterministic-catalogue doctrine).
  * Attribution: "A product of ArchLife". Hosting: pulse-ai.archlife.in.

Data is synthetic only (Kaggle datasets are not bundled; deterministic seeds stand in).
"""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml

ATTRIBUTION = "A product of ArchLife"
HOSTING = "pulse-ai.archlife.in"

# The 5 universal cycle stages, in flywheel order. Sector-blind; named per profile.
UNIVERSAL_STAGES = ["spend", "revenue", "retention", "expansion", "referral"]

# Demo display order for the init-page toggle (Healthcare default + deepest first).
SECTOR_ORDER = [
    "healthcare", "retail", "saas", "automotive", "hospitality", "financial_services"
]

_PROFILE_DIR = Path(__file__).resolve().parent / "sectors"

# Generic-but-credible cohort + location names per sector (synthetic, no real brands).
_COHORTS = {
    "healthcare": ["Ortho recall", "Implant follow-up", "Lapsed hygiene"],
    "retail": ["Festive buyers", "Electronics upgraders", "Dormant loyalty"],
    "saas": ["Power accounts", "At-risk renewals", "Expansion-ready"],
    "automotive": ["Service-due owners", "Upgrade-eligible", "Warranty-lapsing"],
    "hospitality": ["Repeat guests", "Anniversary segment", "Lapsed bookers"],
    "financial_services": ["HNW review-due", "Wallet-expansion", "Dormant clients"],
}
_LOCATIONS = {
    "healthcare": ["Kamla Nagar", "Indiranagar", "Bandra", "Whitefield"],
    "retail": ["Indiranagar flagship", "Bandra flagship", "Koramangala", "CP store"],
    "saas": ["Bangalore IT-park", "Gurugram cluster", "Pune accounts", "Hyderabad"],
    "automotive": ["Tier-1 metro", "South dealership", "West dealership", "North hub"],
    "hospitality": ["Goa resort", "Udaipur palace", "Kerala backwaters", "Jaipur"],
    "financial_services": ["Private bank — South", "West branch", "North branch", "Metro HNW"],
}


# ---------------------------------------------------------------------------
# Deterministic seeding (no runtime randomness; stable across runs)
# ---------------------------------------------------------------------------
def _unit(*parts: str) -> float:
    """Stable float in [0, 1) seeded by the joined parts."""
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def _round1(x: float) -> float:
    return round(x, 1)


# ---------------------------------------------------------------------------
# Profile loading
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _load_profiles() -> dict:
    profiles = {}
    for path in sorted(_PROFILE_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        profiles[data["sector"]] = data
    return profiles


def list_sector_ids() -> list:
    profiles = _load_profiles()
    return [s for s in SECTOR_ORDER if s in profiles]


def get_profile(sector: str) -> Optional[dict]:
    return _load_profiles().get(sector)


def default_sector() -> str:
    for sid, p in _load_profiles().items():
        if p.get("default"):
            return sid
    return list_sector_ids()[0]


# ---------------------------------------------------------------------------
# LTV:CAC band helpers
# ---------------------------------------------------------------------------
def band_label(ltv_cac: float) -> str:
    """Global reference bands: 2:1 baseline, 3:1 target, 4:1 stretch."""
    if ltv_cac < 2.0:
        return "below baseline"
    if ltv_cac < 3.0:
        return "baseline"
    if ltv_cac < 4.0:
        return "target"
    return "stretch"


# ---------------------------------------------------------------------------
# The coercion: every sector -> one canonical shape
# ---------------------------------------------------------------------------
def _stage_ltv_cac(sector: str, profile: dict) -> list:
    """5 universal stages with deterministic per-stage LTV:CAC.

    The binding-constraint stage is rendered as the visible drag (below band floor);
    the others spread from the band floor up past the headline.
    """
    headline = float(profile["headline"]["ltv_cac"])
    low, high = (float(x) for x in profile["headline"]["band"])
    constraint = profile["headline"]["binding_constraint"]
    labels = profile.get("stage_labels", {})

    stages = []
    for stage in UNIVERSAL_STAGES:
        if stage == constraint:
            # The binding constraint: clearly the weakest stage, below the band floor.
            value = _round1(low - 0.3 - 0.4 * _unit(sector, stage))
        else:
            # Spread the healthy stages from band floor to a touch above headline.
            value = _round1(low + (high - low + 0.4) * _unit(sector, stage))
        stages.append({
            "id": stage,
            "label": labels.get(stage, stage.title()),
            "ltv_cac": value,
            "in_band": low <= value <= high,
            "is_constraint": stage == constraint,
        })
    return stages


def _cohorts(sector: str, profile: dict) -> list:
    headline = float(profile["headline"]["ltv_cac"])
    out = []
    for i, name in enumerate(_COHORTS.get(sector, [])):
        j = _unit(sector, "cohort", name)
        out.append({
            "id": f"{sector}-cohort-{i+1}",
            "name": name,
            "ltv_cac": _round1(headline - 0.6 + 1.4 * j),
            "customers": 40 + int(360 * _unit(sector, "size", name)),
        })
    return out


def _locations(sector: str, profile: dict) -> list:
    headline = float(profile["headline"]["ltv_cac"])
    out = []
    for i, name in enumerate(_LOCATIONS.get(sector, [])):
        j = _unit(sector, "loc", name)
        out.append({
            "id": f"{sector}-loc-{i+1}",
            "name": name,
            "ltv_cac": _round1(headline - 0.5 + 1.2 * j),
        })
    return out


def coerce(sector: str) -> Optional[dict]:
    """Coerce a sector's YAML profile into the canonical unified shape.

    Returns the same shape for every sector -- one schema, six sector-shaped datasets.
    """
    profile = get_profile(sector)
    if not profile:
        return None

    headline = float(profile["headline"]["ltv_cac"])
    low, high = (float(x) for x in profile["headline"]["band"])
    constraint = profile["headline"]["binding_constraint"]
    stages = _stage_ltv_cac(sector, profile)
    constraint_label = next(
        (s["label"] for s in stages if s["id"] == constraint), constraint.title()
    )

    return {
        "sector": sector,
        "display_name": profile["display_name"],
        "depth": profile.get("depth", "stub"),
        "reference": profile.get("reference"),
        "is_default": bool(profile.get("default")),
        "attribution": ATTRIBUTION,
        "hosting": HOSTING,
        "labels": profile.get("labels", {}),
        "headline": {
            "ltv_cac": headline,
            "band": [low, high],
            "band_label": band_label(headline),
            "binding_constraint": constraint,
            "binding_constraint_label": constraint_label,
        },
        "stages": stages,
        "cohorts": _cohorts(sector, profile),
        "locations": _locations(sector, profile),
        "governance": {
            "rulesets": profile.get("rulesets", []),
            "protocols": profile.get("protocols", {}),
            "policies": profile.get("policies", {}),
            "cadences": profile.get("cadences", {}),
        },
    }


def list_sectors() -> list:
    """Lightweight list for the init-page toggle (no drill data)."""
    out = []
    for sid in list_sector_ids():
        p = get_profile(sid)
        h = p["headline"]
        out.append({
            "sector": sid,
            "display_name": p["display_name"],
            "depth": p.get("depth", "stub"),
            "reference": p.get("reference"),
            "is_default": bool(p.get("default")),
            "ltv_cac": float(h["ltv_cac"]),
            "band": [float(h["band"][0]), float(h["band"][1])],
            "band_label": band_label(float(h["ltv_cac"])),
        })
    return out
