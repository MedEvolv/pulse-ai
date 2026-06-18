"""Sector governance adapter — the second adapter (ADR-0002).

The first adapter is the deterministic engine (the catalogue). This is the
second: it loads the sector governance YAML profiles (backend/sectors/*.yaml)
and exposes a typed SectorProfile. The engine consumes governance as config,
not code — to add a 7th sector, drop in one YAML file.

(backend/sectors.py is the API-facing coercion/registry over the same YAML;
this module is the engine-facing typed adapter. Both read the one canonical
source — the YAML files — so they cannot diverge.)
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, ConfigDict

# The 5 universal cycle stages (Spend -> Revenue -> Retention -> Expansion -> Referral).
CYCLE_STAGES = ["spend", "revenue", "retention", "expansion", "referral"]

_PROFILE_DIR = Path(__file__).resolve().parent.parent / "sectors"


class SectorProfile(BaseModel):
    """Typed view of one sector governance YAML profile."""

    model_config = ConfigDict(extra="ignore")

    sector: str
    display_name: str
    depth: str
    stage_labels: dict
    rulesets: list
    protocols: dict
    policies: dict
    cadences: dict
    ltv_cac: float
    band: list
    binding_constraint: str

    def stage_label(self, stage: str) -> str:
        """Sector-shaped name for a universal cycle stage."""
        return self.stage_labels.get(stage, stage.title())

    def cycle_stages(self) -> list:
        return list(CYCLE_STAGES)


def _raw(sector_id: str) -> Optional[dict]:
    path = _PROFILE_DIR / f"{sector_id}.yaml"
    if not path.exists():
        return None
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=16)
def load_sector(sector_id: str) -> Optional[SectorProfile]:
    """Load and validate one sector governance profile. None if unknown."""
    d = _raw(sector_id)
    if not d:
        return None
    h = d["headline"]
    return SectorProfile(
        sector=d["sector"],
        display_name=d["display_name"],
        depth=d.get("depth", "stub"),
        stage_labels=d.get("stage_labels", {}),
        rulesets=d.get("rulesets", []),
        protocols=d.get("protocols", {}),
        policies=d.get("policies", {}),
        cadences=d.get("cadences", {}),
        ltv_cac=float(h["ltv_cac"]),
        band=[float(x) for x in h["band"]],
        binding_constraint=h["binding_constraint"],
    )


def list_sectors() -> list:
    return sorted(p.stem for p in _PROFILE_DIR.glob("*.yaml"))
