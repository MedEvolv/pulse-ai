"""CP-04: Server-side model spend & latency protection.

Mongo-backed daily run counter, cooldown, response cache, and bounded config.
Fails closed when configuration is absent. Never trusts a browser-supplied count.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone


def _flag(name: str, default: str) -> str:
    return os.environ.get(name, default)


# Tri-state model gate (deepening #3). Public demo default is "off" — deterministic
# only, no budget drained. "synthesized" needs explicit opt-in AND the budget gate.
USE_MODEL_MODES = ("off", "deterministic", "synthesized")


def use_model_mode(requested: str | None = None) -> str:
    """Resolve the effective model mode. Default "off".

    A caller may request a mode; "synthesized" is honored only when the model is
    enabled (MODEL_ENABLED=true). Otherwise it degrades to "deterministic" so the
    public demo can never drain budget. Unknown requests -> "off".
    """
    env_default = _flag("MODEL_USE_MODE", "off").lower()
    mode = (requested or env_default or "off").lower()
    if mode not in USE_MODEL_MODES:
        return "off"
    if mode == "synthesized" and _flag("MODEL_ENABLED", "false").lower() != "true":
        return "deterministic"   # opt-in present but model disabled -> deterministic, no spend
    return mode


def config() -> dict:
    return {
        "enabled": _flag("MODEL_ENABLED", "false").lower() == "true",
        "use_model_default": _flag("MODEL_USE_MODE", "off").lower(),
        "daily_limit": int(_flag("MODEL_DAILY_RUN_LIMIT", "25")),
        "min_seconds_between_runs": int(_flag("MODEL_MIN_SECONDS_BETWEEN_RUNS", "20")),
        "timeout_seconds": int(_flag("MODEL_TIMEOUT_SECONDS", "12")),
        "cache_ttl_seconds": int(_flag("MODEL_CACHE_TTL_SECONDS", "86400")),
        "max_output_tokens": int(_flag("MODEL_MAX_OUTPUT_TOKENS", "700")),
    }


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def cache_key(region: str, role: str, question: str, facts_hash: str) -> str:
    norm = f"{region}|{role}|{(question or '').strip().lower()}|{facts_hash}"
    return "MC-" + hashlib.sha256(norm.encode()).hexdigest()[:32]


def facts_hash(facts: dict) -> str:
    import json
    payload = json.dumps(facts, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


async def get_state(db) -> dict:
    cfg = config()
    date = _today_utc()
    doc = await db.model_budget.find_one({"date_utc": date}) or {}
    new_runs = doc.get("new_runs", 0)
    return {
        "date_utc": date,
        "enabled": cfg["enabled"],
        "daily_limit": cfg["daily_limit"],
        "new_runs": new_runs,
        "cache_hits": doc.get("cache_hits", 0),
        "remaining": max(0, cfg["daily_limit"] - new_runs),
        "cooldown_seconds": cfg["min_seconds_between_runs"],
        "timeout_seconds": cfg["timeout_seconds"],
        "max_output_tokens": cfg["max_output_tokens"],
        "last_run_at": doc.get("last_run_at"),
        "last_reason_code": doc.get("last_reason_code"),
    }


async def check_allowed(db) -> tuple:
    """(allowed, reason_code). Enforces enabled flag, daily limit, cooldown."""
    cfg = config()
    if not cfg["enabled"]:
        return False, "MODEL_DISABLED"
    date = _today_utc()
    doc = await db.model_budget.find_one({"date_utc": date}) or {}
    if doc.get("new_runs", 0) >= cfg["daily_limit"]:
        return False, "MODEL_BUDGET_EXHAUSTED"
    last = doc.get("last_run_at")
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
            elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds()
            if elapsed < cfg["min_seconds_between_runs"]:
                return False, "MODEL_COOLDOWN_ACTIVE"
        except Exception:
            pass
    return True, None


async def record_run(db, reason_code=None):
    date = _today_utc()
    await db.model_budget.update_one(
        {"date_utc": date},
        {"$inc": {"new_runs": 1},
         "$set": {"last_run_at": datetime.now(timezone.utc).isoformat(),
                  "last_reason_code": reason_code}},
        upsert=True,
    )


async def record_cache_hit(db):
    date = _today_utc()
    await db.model_budget.update_one(
        {"date_utc": date}, {"$inc": {"cache_hits": 1}}, upsert=True)


async def record_reason(db, reason_code):
    date = _today_utc()
    await db.model_budget.update_one(
        {"date_utc": date}, {"$set": {"last_reason_code": reason_code}}, upsert=True)


async def cache_get(db, key: str):
    cfg = config()
    doc = await db.model_cache.find_one({"_id": key})
    if not doc:
        return None
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(doc["stored_at"])).total_seconds()
        if age > cfg["cache_ttl_seconds"]:
            return None
    except Exception:
        return None
    return doc.get("brief")


async def cache_set(db, key: str, brief: dict):
    await db.model_cache.update_one(
        {"_id": key},
        {"$set": {"brief": brief, "stored_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
