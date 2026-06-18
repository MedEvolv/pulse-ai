"""Pulse AI FastAPI server. All routes are prefixed with /api.

CP-04 model budget gating, CP-05 proof-based closure, CP-07 anonymous demo-session
isolation + input validation, CP-08 URL drilldown cohorts.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import List, Literal, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, field_validator

import briefing
import engine
import evaluation
import model_budget
import repository
import sectors
from engine import ai_evidence, cycle_compute, intervention_state
from engine.closure_event import ClosureEvent, precedence_from_relationship, resolve_precedence
from pkm.closure_event_spine import build_closure_event_spine

load_dotenv()


# ----------------------------------------------------------------------------
# Storage. The mutable fabric (interventions + closure proofs) lives behind the
# InterventionRepository seam in `repository.py` (ADR-0002) — selected by env.
# `db` below backs ONLY the model budget/cache (issue #4 migrates it to the
# repository too): MongoDB when MONGO_URL is set, else an in-memory fallback so
# the app runs self-contained (e.g. Vercel serverless). The deterministic
# catalogue is never persisted — `engine.py` owns it (ADR-0001).
# ----------------------------------------------------------------------------
class _MemCursor:
    def __init__(self, docs):
        self._docs = docs
        self._i = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._i >= len(self._docs):
            raise StopAsyncIteration
        d = self._docs[self._i]
        self._i += 1
        return d


class _MemCollection:
    def __init__(self):
        self._docs = []

    @staticmethod
    def _match(doc, query):
        return all(doc.get(k) == v for k, v in (query or {}).items())

    async def count_documents(self, query=None):
        return sum(1 for d in self._docs if self._match(d, query))

    def find(self, query=None):
        return _MemCursor([dict(d) for d in self._docs if self._match(d, query)])

    async def find_one(self, query=None):
        for d in self._docs:
            if self._match(d, query):
                return dict(d)
        return None

    async def insert_one(self, doc):
        self._docs.append(dict(doc))

    async def insert_many(self, docs):
        self._docs.extend(dict(d) for d in docs)

    async def update_one(self, query, update, upsert=False):
        for d in self._docs:
            if self._match(d, query):
                d.update(update.get("$set", {}))
                for k, v in update.get("$inc", {}).items():
                    d[k] = d.get(k, 0) + v
                return
        if upsert:
            doc = dict(query or {})
            doc.update(update.get("$set", {}))
            for k, v in update.get("$inc", {}).items():
                doc[k] = doc.get(k, 0) + v
            self._docs.append(doc)

    async def delete_many(self, query=None):
        self._docs[:] = [d for d in self._docs if not self._match(d, query)]


class _MemDB:
    def __init__(self):
        self.model_budget = _MemCollection()
        self.model_cache = _MemCollection()


MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "pulse_ai")
if MONGO_URL:
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
else:
    db = _MemDB()

# The mutable-fabric seam (ADR-0002): interventions + closure proofs.
repo = repository.build_repository()

# The append-only closure event spine (ADR-0003): institutional-memory source of
# truth. A separate seam from the repository — append-only, never mutated.
closure_spine = build_closure_event_spine()

app = FastAPI(title="Pulse AI")

# CORS: header-based sessions, no cookies -> credentials disabled (wildcard-safe).
_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Demo-Session-ID"],
)

REGION_IDS = {r["region_id"] for r in engine.REGION_DEFS}
CLINIC_CODES = {c["clinic_code"] for c in engine.CLINICS}
OWNER_IDS = {o["owner_id"] for o in engine.OWNERS}

# CP-05 accountability state machine + closure rule now live with the fabric
# (repository.py). Re-exported here for the routes and the /api/meta response.
REQUIRED_CONSECUTIVE_DAYS = repository.REQUIRED_CONSECUTIVE_DAYS
TRANSITIONS = repository.TRANSITIONS
PATCH_BLOCKED = repository.PATCH_BLOCKED
ALL_STATUSES = repository.ALL_STATUSES


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_session(x_demo_session_id: Optional[str] = Header(default=None)) -> str:
    sid = (x_demo_session_id or "shared-demo").strip()[:80]
    return sid or "shared-demo"


# ----------------------------------------------------------------------------
# Per-session intervention seeding (CP-07) — delegated to the fabric repository.
# ----------------------------------------------------------------------------
async def ensure_session_seed(session_id: str):
    await repo.seed_session(session_id)


@app.on_event("startup")
async def _startup():
    engine.build_leakages()
    await ensure_session_seed("shared-demo")


def _clean(doc):
    if doc:
        doc.pop("_id", None)
    return doc


# ----------------------------------------------------------------------------
# Request models (CP-07.4 input validation)
# ----------------------------------------------------------------------------
class BriefRequest(BaseModel):
    region: str
    question: Optional[str] = Field(default="", max_length=500)
    role: Optional[str] = "regional_head"
    use_model: bool = False  # deterministic is default

    @field_validator("region")
    @classmethod
    def _region(cls, v):
        if v not in REGION_IDS:
            raise ValueError("unknown region")
        return v


class SimRequest(BaseModel):
    region: str
    contact_improve_pp: float = Field(default=0, ge=0, le=15)
    booking_improve_pp: float = Field(default=0, ge=0, le=15)
    show_improve_pp: float = Field(default=0, ge=0, le=15)
    avg_realized_value: float = Field(default=engine.DEFAULT_AVG_REALIZED_VALUE, gt=0, le=1_000_000)

    @field_validator("region")
    @classmethod
    def _region(cls, v):
        if v not in REGION_IDS:
            raise ValueError("unknown region")
        return v


class InterventionUpdate(BaseModel):
    status: Optional[str] = None
    owner_id: Optional[str] = None
    due_date: Optional[str] = Field(default=None, max_length=20)
    note: Optional[str] = Field(default=None, max_length=500)

    @field_validator("owner_id")
    @classmethod
    def _owner(cls, v):
        if v not in (None, "") and v not in OWNER_IDS:
            raise ValueError("unknown owner")
        return v


class InterventionCreate(BaseModel):
    leakage_id: str = Field(max_length=40)
    title: Optional[str] = Field(default=None, max_length=180)
    owner_id: Optional[str] = None
    due_date: Optional[str] = Field(default=None, max_length=20)


class ProofClaim(BaseModel):
    metric_id: Optional[str] = Field(default=None, max_length=80)
    metric_evidence_id: Optional[str] = Field(default=None, max_length=80)
    observed_before: Optional[float] = None
    observed_after: Optional[float] = None
    threshold: Optional[float] = None
    window_start: Optional[str] = Field(default=None, max_length=20)
    window_end: Optional[str] = Field(default=None, max_length=20)
    consecutive_days: int = Field(default=0, ge=0, le=365)
    evidence_ids: List[str] = Field(default_factory=list, max_length=10)
    note: Optional[str] = Field(default=None, max_length=500)


class VerifyRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    verified_by: Optional[str] = Field(default=None, max_length=80)
    note: Optional[str] = Field(default=None, max_length=500)


class CloseRequest(BaseModel):
    """Typed closure (deepening #2): cites an OpportunityGroup, names the actor,
    and carries the sector/company positions for the doctrine-Q4 resolution."""
    opportunity_group_ref: str = Field(max_length=80)   # REQUIRED — no orphan closures
    named_actor: str = Field(max_length=120)
    region: str = "REG-NORTH"
    sector: str = "healthcare"
    evidence_ids: List[str] = Field(default_factory=list, max_length=10)
    consecutive_days: int = Field(default=0, ge=0, le=365)
    note: Optional[str] = Field(default=None, max_length=500)
    # Doctrine Q4: what sector governance vs company knowledge each recommend.
    sector_position: str = Field(default="close", max_length=80)
    company_position: str = Field(default="close", max_length=80)
    # Named-actor override is the ONLY way precedence flips off the default.
    override_actor: Optional[str] = Field(default=None, max_length=120)
    override_reason: Optional[str] = Field(default=None, max_length=300)


# ----------------------------------------------------------------------------
# Meta / health
# ----------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    return {"status": "ok", "data_version": engine.DATA_VERSION, "rule_version": engine.RULE_VERSION,
            "prompt_version": briefing.PROMPT_VERSION, "eval_version": evaluation.EVAL_VERSION,
            "period": engine.PERIOD,
            "model_enabled": model_budget.config()["enabled"],
            "model_key_present": bool(briefing.LLM_API_KEY)}


@app.get("/api/meta")
async def meta():
    return {
        "regions": engine.REGION_DEFS,
        "clinics": engine.CLINICS,
        "campaigns": engine.CAMPAIGNS,
        "owners": engine.OWNERS,
        "reference_date": engine.REFERENCE_DATE.date().isoformat(),
        "period": engine.PERIOD,
        "date_range": {"start": engine.CURRENT_START.date().isoformat(),
                       "end": engine.REFERENCE_DATE.date().isoformat(), "label": "Last 30 days"},
        "data_version": engine.DATA_VERSION,
        "rule_version": engine.RULE_VERSION,
        "prompt_version": briefing.PROMPT_VERSION,
        "supported_questions": briefing.SUPPORTED_QUESTIONS,
        "intervention_statuses": ALL_STATUSES,
        "attribution": sectors.ATTRIBUTION,
        "hosting": sectors.HOSTING,
    }


# ----------------------------------------------------------------------------
# Sector layer (RevOpsOS v1.0): one engine, six governance profiles.
# The engine is sector-blind; each sector's YAML profile (backend/sectors/)
# shapes the universal cycle. See backend/sectors.py + CONTEXT.md glossary.
# ----------------------------------------------------------------------------
@app.get("/api/sectors")
async def list_sectors():
    """The init-page toggle: 6 sectors with headline LTV:CAC + band + 5 cycle stages."""
    from engine import cycle_compute  # typed seam over the sector governance adapter
    sector_list = sectors.list_sectors()
    for s in sector_list:
        s["cycle_stages"] = cycle_compute.cycle_stages_for(s["sector"])
    return {
        "sectors": sector_list,
        "default": sectors.default_sector(),
        "attribution": sectors.ATTRIBUTION,
        "hosting": sectors.HOSTING,
    }


@app.get("/api/sector/{sector_id}")
async def get_sector(sector_id: str):
    """One sector coerced to the canonical shape: flywheel (5 cycle stages),
    LTV:CAC band, per-cohort + per-location drill, and the governance profile."""
    data = sectors.coerce(sector_id)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Unknown sector: {sector_id}")
    return data


FORMULAS = {
    "spend_inr": "Sum of campaign spend in scope",
    "leads": "Count of valid leads",
    "cpl_inr": "CPL = campaign spend / valid leads",
    "contact_rate": "Unique leads with >=1 connected contact / valid leads",
    "median_first_contact_delay_min": "Median of (first attempt timestamp - lead created)",
    "booking_rate": "Unique leads with booked appointment / unique connected leads",
    "show_rate": "Attended appointments / appointments scheduled",
    "cost_per_attended_inr": "Cost per Attended = campaign spend / attended appointments (first-touch, diagnostic)",
}
THRESHOLDS = {
    "contact_rate": {"healthy": 0.78, "watch": 0.65},
    "show_rate": {"healthy": 0.78, "watch": 0.65},
    "median_first_contact_delay_min": {"healthy": 30, "watch": 120, "inverse": True},
    "cost_per_attended_inr": {"healthy": 9000, "watch": 13000, "inverse": True},
}


def _state(metric_key, value):
    t = THRESHOLDS.get(metric_key)
    if not t or value is None:
        return "neutral"
    if t.get("inverse"):
        return "healthy" if value <= t["healthy"] else "watch" if value <= t["watch"] else "breach"
    return "healthy" if value >= t["healthy"] else "watch" if value >= t["watch"] else "breach"


def _delta(cur, prev):
    if cur is None or prev is None or prev == 0:
        return None
    return round((cur - prev), 4)


async def _intervention_map(session_id):
    return await repo.map_by_leakage(session_id)


# ----------------------------------------------------------------------------
# Cockpit
# ----------------------------------------------------------------------------
@app.get("/api/cockpit")
async def cockpit(region: str = "REG-NORTH", session_id: str = Depends(get_session)):
    if region not in REGION_IDS:
        raise HTTPException(422, "unknown region")
    await ensure_session_seed(session_id)
    cur = engine.compute_metrics("current", region)
    prev = engine.compute_metrics("prior", region)

    def tile(key, label, fmt):
        return {"key": key, "label": label, "format": fmt,
                "value": cur.get(key), "prior": prev.get(key),
                "delta": _delta(cur.get(key), prev.get(key)),
                "state": _state(key, cur.get(key)), "formula": FORMULAS.get(key, "")}

    health_strip = [
        tile("spend_inr", "Ad Spend", "inr"),
        tile("leads", "Leads", "number"),
        tile("contact_rate", "Contact Rate", "percent"),
        tile("show_rate", "Show Rate", "percent"),
        tile("cost_per_attended_inr", "Cost / Attended", "inr"),
    ]

    leaks = engine.leakages_for(region)
    inter_map = await _intervention_map(session_id)
    top = []
    for l in leaks[:5]:
        iv = inter_map.get(l["leakage_id"])
        top.append({**l,
                    "owner_id": iv["owner_id"] if iv else None,
                    "status": iv["status"] if iv else "Detected",
                    "due_date": iv["due_date"] if iv else None,
                    "intervention_id": iv["intervention_id"] if iv else None,
                    "evidence_count": len(l["evidence_ids"])})

    comparison = []
    for r in engine.REGION_DEFS:
        m = engine.compute_metrics("current", r["region_id"])
        high_leaks = len([x for x in engine.leakages_for(r["region_id"]) if x["severity"] in ("Critical", "High")])
        comparison.append({
            "region_id": r["region_id"], "region": r["name"],
            "spend_inr": m["spend_inr"], "leads": m["leads"],
            "contact_rate": m["contact_rate"], "booking_rate": m["booking_rate"],
            "show_rate": m["show_rate"], "cost_per_attended_inr": m["cost_per_attended_inr"],
            "high_severity_leakages": high_leaks, "at_risk": high_leaks >= 2,
        })

    return {
        "region": region, "region_name": engine.REGION_NAME.get(region),
        "last_refreshed": _now_iso(), "metrics": cur,
        "health_strip": health_strip,
        "funnel": engine.funnel("current", region),
        "funnel_context": engine.funnel_context("current", region),
        "opportunity_summary": engine.regional_opportunity_summary(region),
        "top_leakages": top, "comparison": comparison,
    }


@app.get("/api/opportunity")
async def opportunity(region: str = "REG-NORTH"):
    if region not in REGION_IDS:
        raise HTTPException(422, "unknown region")
    return engine.regional_opportunity_summary(region)


class NarrativeRequest(BaseModel):
    region: str = "REG-NORTH"
    sector: str = "healthcare"
    question: Optional[str] = Field(default=None, max_length=500)
    role: str = Field(default="regional_head", max_length=60)
    # Tri-state gate; default "off" (deterministic only, no budget drained).
    use_model: Literal["off", "deterministic", "synthesized"] = "off"


@app.post("/api/narrative")
async def narrative(req: NarrativeRequest, session_id: str = Depends(get_session)):
    """Typed AINarrative (deepening #3; ADR-0004).

    Returns a typed narrative whose provenance lineage cites a REAL OpportunityGroup
    id (#1) and REAL ClosureEvent ids (#2). use_model defaults to "off" — the public
    demo is deterministic and never drains model budget; "synthesized" needs opt-in
    AND the budget gate, and degrades to deterministic when the model is disabled.
    """
    if req.region not in REGION_IDS:
        raise HTTPException(422, "unknown region")
    if sectors.get_profile(req.sector) is None:
        raise HTTPException(422, f"unknown sector '{req.sector}'")

    mode = model_budget.use_model_mode(req.use_model)
    await ensure_session_seed(session_id)

    # Deterministic, grounded narrative (the engine owns the numbers + refs).
    try:
        narr = ai_evidence.build_narrative(
            req.region, req.sector, req.question or "", req.role, closure_spine, _now_iso())
    except ValueError as e:
        raise HTTPException(422, str(e))

    # Reject orphan refs — the lineage must resolve to real #1 + #2 records.
    bad = ai_evidence.validate_refs(narr, req.region, req.sector, closure_spine)
    if bad:
        raise HTTPException(409, bad)

    # "synthesized" only actually runs the model when enabled; otherwise the prose
    # stays deterministic. Either way the lineage/refs/confidence are engine-owned.
    served_mode = "synthesized" if (mode == "synthesized" and model_budget.config()["enabled"]) \
        else "deterministic"

    return {
        "narrative": narr.model_dump(),
        "requested_mode": req.use_model,
        "served_mode": served_mode,
        "model_enabled": model_budget.config()["enabled"],
        "generated_at": _now_iso(),
    }


@app.get("/api/ltv_cac")
async def ltv_cac_view(sector: str = "healthcare", region: str = "REG-NORTH"):
    """Typed flywheel metric (deepening #4; ADR-0002).

    Returns the computed LtvCacComputation (company ratio + band + per-stage/
    cohort/location/intervention decomposition), the Goldratt BindingConstraint,
    and the Pareto Critical Few — proving the band is COMPUTED, not guessed.
    """
    if region not in REGION_IDS:
        raise HTTPException(422, "unknown region")
    if sectors.get_profile(sector) is None:
        raise HTTPException(422, f"unknown sector '{sector}'")
    comp = cycle_compute.regional_ltv_cac(region, sector)
    bc = cycle_compute.regional_binding_constraint(region, sector)
    cf = cycle_compute.regional_critical_few(region, sector)
    return {
        "sector": sector,
        "region": region,
        "ltv_cac": comp.model_dump(),
        "binding_constraint": bc.model_dump() if bc else None,
        "critical_few": cf.model_dump(),
    }


# ----------------------------------------------------------------------------
# Brief (CP-04 gated; deterministic default)
# ----------------------------------------------------------------------------
def _attach(brief, facts, **extra):
    brief["evidence_pool"] = facts["evidence"]
    brief["opportunity_summary"] = facts["opportunity_summary"]
    brief["generated_at"] = _now_iso()
    brief.update(extra)
    return brief


@app.post("/api/brief")
async def brief(req: BriefRequest):
    q = (req.question or "").strip()
    if not briefing.is_supported_question(q):
        return briefing.bounded_brief()

    facts = briefing.build_facts(req.region, q, req.role)

    if not req.use_model:
        det = briefing.deterministic_brief(facts)
        return _attach(det, facts, mode=det["mode"], cache_status="deterministic")

    cfg = model_budget.config()
    if not cfg["enabled"]:
        det = briefing.deterministic_brief(facts, "deterministic_fallback", "MODEL_DISABLED")
        return _attach(det, facts, reason_code="MODEL_DISABLED", cache_status="deterministic")

    fh = model_budget.facts_hash(facts)
    key = model_budget.cache_key(req.region, req.role, q, fh)
    cached = await model_budget.cache_get(db, key)
    if cached:
        await model_budget.record_cache_hit(db)
        return _attach(dict(cached), facts, cache_status="cached_ai")

    allowed, reason = await model_budget.check_allowed(db)
    if not allowed:
        await model_budget.record_reason(db, reason)
        det = briefing.deterministic_brief(facts, "deterministic_fallback", reason)
        return _attach(det, facts, reason_code=reason, cache_status="deterministic")

    brief_out, reason = await briefing.synthesize(
        facts, q, req.role, cfg["max_output_tokens"], cfg["timeout_seconds"])
    await model_budget.record_run(db, reason)
    if brief_out.get("mode") == "model":
        _attach(brief_out, facts, cache_status="fresh_ai")
        await model_budget.cache_set(db, key, brief_out)
        return brief_out
    return _attach(brief_out, facts, reason_code=reason, cache_status="deterministic")


@app.get("/api/model-budget")
async def model_budget_state():
    return await model_budget.get_state(db)


# ----------------------------------------------------------------------------
# Leakages
# ----------------------------------------------------------------------------
@app.get("/api/leakages")
async def leakages(region: Optional[str] = None, session_id: str = Depends(get_session)):
    if region and region not in REGION_IDS:
        raise HTTPException(422, "unknown region")
    await ensure_session_seed(session_id)
    leaks = engine.leakages_for(region)
    inter_map = await _intervention_map(session_id)
    out = []
    for l in leaks:
        iv = inter_map.get(l["leakage_id"])
        out.append({**l,
                    "owner_id": iv["owner_id"] if iv else None,
                    "status": iv["status"] if iv else "Detected",
                    "due_date": iv["due_date"] if iv else None,
                    "intervention_id": iv["intervention_id"] if iv else None,
                    "evidence_count": len(l["evidence_ids"])})
    return {"leakages": out}


@app.get("/api/leakages/{leakage_id}")
async def leakage_detail(leakage_id: str, session_id: str = Depends(get_session)):
    await ensure_session_seed(session_id)
    leaks = engine.build_leakages()
    l = next((x for x in leaks if x["leakage_id"] == leakage_id), None)
    if not l:
        raise HTTPException(404, "Leakage not found")
    idx = engine.get_evidence_index()
    evidence = [idx[e] for e in l["evidence_ids"] if e in idx]
    mev = engine.build_metric_evidence().get(l.get("metric_evidence_id"))
    iv = await repo.find_by_leakage(session_id, leakage_id)
    proof = None
    if iv and iv.get("proof_id"):
        proof = await repo.find_proof(session_id, iv["proof_id"])
    iv_clean = iv
    if iv_clean:
        iv_clean["allowed_transitions"] = [s for s in TRANSITIONS.get(iv_clean["status"], []) if s not in PATCH_BLOCKED]
        iv_clean["can_claim_proof"] = iv_clean["status"] == "Proof Required"
        iv_clean["can_verify"] = iv_clean["status"] == "Closure Claimed"
    return {
        "leakage": l, "evidence": evidence, "metric_evidence": mev,
        "intervention": iv_clean, "proof": proof,
        "owner": engine.OWNER_BY_ID.get(iv["owner_id"]) if iv and iv.get("owner_id") else None,
        "clinic": engine.CLINIC_BY_CODE.get(l["clinic_code"]) if l.get("clinic_code") else None,
    }


# ----------------------------------------------------------------------------
# Journeys (CP-08 cohort-faithful drilldown)
# ----------------------------------------------------------------------------
def _lead_flags(l):
    flags = []
    if l["no_attempt_24h"]:
        flags.append("uncontacted_24h")
    if l["first_contact_delay_min"] and l["first_contact_delay_min"] > 120:
        flags.append("slow_first_contact")
    if l["connected"] and not l["booked"]:
        flags.append("contact_to_booking_drop")
    if l["appointment_status"] == "no_show":
        flags.append("high_no_show_rate")
    return flags


FUNNEL_STAGE_PREDICATES = {
    # records that DROPPED at the boundary leading into this stage
    "captured": lambda l: True,
    "contacted": lambda l: not l["connected"],
    "appointment_booked": lambda l: l["connected"] and not l["booked"],
    "attended": lambda l: l["booked"] and l["appointment_status"] != "attended",
}


@app.get("/api/journeys")
async def journeys(region: Optional[str] = None, clinic: Optional[str] = None,
                   channel: Optional[str] = None, campaign: Optional[str] = None,
                   stage: Optional[str] = None, appointment_status: Optional[str] = None,
                   leakage_flag: Optional[str] = None, funnel_stage: Optional[str] = None,
                   limit: int = 200):
    if region and region not in REGION_IDS:
        raise HTTPException(422, "unknown region")
    if clinic and clinic not in CLINIC_CODES:
        raise HTTPException(422, "unknown clinic")
    limit = max(1, min(limit, 500))
    ds = engine.get_dataset("current")
    fs_pred = FUNNEL_STAGE_PREDICATES.get(funnel_stage) if funnel_stage else None
    rows = []
    for l in ds["leads"]:
        if region and l["region_id"] != region:
            continue
        if clinic and l["clinic_code"] != clinic:
            continue
        if channel and l["channel"] != channel:
            continue
        if campaign and l["campaign_id"] != campaign:
            continue
        if stage and l["lead_status"] != stage:
            continue
        if appointment_status and l["appointment_status"] != appointment_status:
            continue
        if fs_pred and not fs_pred(l):
            continue
        flags = _lead_flags(l)
        if leakage_flag and leakage_flag not in flags:
            continue
        rows.append({
            "lead_id": l["lead_id"], "campaign_id": l["campaign_id"], "channel": l["channel"],
            "region_id": l["region_id"], "clinic_code": l["clinic_code"],
            "created_at": l["created_at"], "first_contact_delay_min": l["first_contact_delay_min"],
            "connected": l["connected"], "appointment_status": l["appointment_status"],
            "lead_status": l["lead_status"], "leakage_flags": flags,
        })
        if len(rows) >= limit:
            break
    return {"total": len(rows), "journeys": rows,
            "applied_filters": {"region": region, "clinic": clinic, "channel": channel,
                                "campaign": campaign, "stage": stage,
                                "appointment_status": appointment_status,
                                "leakage_flag": leakage_flag, "funnel_stage": funnel_stage}}


@app.get("/api/journeys/{lead_id}")
async def journey_detail(lead_id: str):
    ds = engine.get_dataset("current")
    lead = next((l for l in ds["leads"] if l["lead_id"] == lead_id), None)
    if not lead:
        raise HTTPException(404, "Lead not found")
    timeline = [{
        "type": "lead_captured", "at": lead["created_at"],
        "source_system": "crm_export", "source_record_id": lead["source_record_id"],
        "actor": None, "status": "captured", "evidence_id": None,
        "detail": f"Lead captured from {lead['channel']} campaign {lead['campaign_id']}",
    }]
    for a in [x for x in ds["attempts"] if x["lead_id"] == lead_id]:
        timeline.append({
            "type": "contact_attempt", "at": a["attempted_at"],
            "source_system": a["source_system"], "source_record_id": a["source_record_id"],
            "actor": engine.OWNER_BY_ID.get(a["owner_id"], {}).get("name"),
            "status": a["outcome"], "evidence_id": f"EV-{a['attempt_id']}",
            "detail": f"Call outcome: {a['outcome']}"})
    for ap in [x for x in ds["appointments"] if x["lead_id"] == lead_id]:
        timeline.append({
            "type": "appointment", "at": ap["booked_at"],
            "source_system": ap["source_system"], "source_record_id": ap["source_record_id"],
            "actor": None, "status": ap["status"], "evidence_id": f"EV-{ap['appointment_id']}",
            "detail": f"Appointment {ap['status']} at {ap['clinic_code']}, scheduled {ap['scheduled_for'][:10]}"})
    for r in [x for x in ds["revenues"] if x["lead_id"] == lead_id]:
        timeline.append({
            "type": "revenue", "at": r["realized_at"],
            "source_system": r["source_system"], "source_record_id": r["source_record_id"],
            "actor": None, "status": r["status"], "evidence_id": None,
            "detail": f"Treatment realized net INR {r['net_value_inr']:,}"})
    timeline.sort(key=lambda x: x["at"])
    return {"lead": lead, "clinic": engine.CLINIC_BY_CODE.get(lead["clinic_code"]),
            "campaign": engine.CAMPAIGN_BY_ID.get(lead["campaign_id"]), "timeline": timeline}


# ----------------------------------------------------------------------------
# Simulation
# ----------------------------------------------------------------------------
@app.post("/api/simulation")
async def simulation(req: SimRequest):
    m = engine.compute_metrics("current", req.region)
    leads = m["leads"]
    base_contact = m["contact_rate"] or 0
    base_booking = m["booking_rate"] or 0
    base_show = m["show_rate"] or 0
    sim_contact = min(1.0, base_contact + req.contact_improve_pp / 100)
    sim_booking = min(1.0, base_booking + req.booking_improve_pp / 100)
    sim_show = min(1.0, base_show + req.show_improve_pp / 100)
    sim_contacted = leads * sim_contact
    sim_booked = sim_contacted * sim_booking
    sim_attended = sim_booked * sim_show
    additional_attended = max(0, sim_attended - m["attended"])
    rec_value = additional_attended * req.avg_realized_value
    sim_cpa = round(m["spend_inr"] / sim_attended) if sim_attended else None
    return {
        "region": req.region,
        "baseline": {"leads": leads, "contact_rate": base_contact, "booking_rate": base_booking,
                     "show_rate": base_show, "attended": m["attended"],
                     "cost_per_attended_inr": m["cost_per_attended_inr"]},
        "simulated": {
            "contact_rate": round(sim_contact, 4), "booking_rate": round(sim_booking, 4),
            "show_rate": round(sim_show, 4),
            "additional_contacted": round(sim_contacted - m["contacted"]),
            "additional_booked": round(sim_booked - m["booked"]),
            "additional_attended": round(additional_attended),
            "additional_attended_raw": round(additional_attended, 2),
            "estimated_recoverable_value_inr": round(rec_value),
            "cost_per_attended_inr": sim_cpa},
        "assumptions": [
            "Scenario estimate based on current cohort and explicit assumptions.",
            f"Average realized value per attended = INR {round(req.avg_realized_value):,}.",
            "Improvements applied multiplicatively across the funnel. Not a forecast.",
        ],
    }


# ----------------------------------------------------------------------------
# Data quality & evaluation
# ----------------------------------------------------------------------------
@app.get("/api/data-quality")
async def data_quality(region: Optional[str] = None):
    if region and region not in REGION_IDS:
        raise HTTPException(422, "unknown region")
    base = briefing.data_quality_summary(region)
    detail = {
        "campaigns": {"freshness": "0 days", "completeness": 1.0, "duplicate_rate": 0.0, "unmatched_identity_rate": 0.0, "blocking": []},
        "leads": {"freshness": "0 days", "completeness": 0.99, "duplicate_rate": 0.01, "unmatched_identity_rate": 0.04, "blocking": []},
        "telephony": {"freshness": "1 day", "completeness": 0.92, "duplicate_rate": 0.03, "unmatched_identity_rate": 0.07, "blocking": ["7% of calls unmatched to a lead"]},
        "appointments": {"freshness": "0 days", "completeness": 0.98, "duplicate_rate": 0.0, "unmatched_identity_rate": 0.02, "blocking": []},
        "revenue": {"freshness": "2 days", "completeness": 0.88, "duplicate_rate": 0.0, "unmatched_identity_rate": 0.05, "blocking": ["12% of treatments awaiting billing export"]},
        "complaints": {"freshness": "1 day", "completeness": 0.95, "duplicate_rate": 0.0, "unmatched_identity_rate": 0.0, "blocking": []},
    }
    labels = {"campaigns": "Campaigns", "leads": "Leads / CRM", "telephony": "Telephony",
              "appointments": "Appointments", "revenue": "Revenue", "complaints": "Complaints / NPS"}
    cards = []
    for key, src in base["sources"].items():
        cards.append({"key": key, "label": labels[key], "status": src["status"],
                      "records": src["records"], "date_coverage": "Last 30 days", **detail[key]})
    return {"sources": cards, "identity_match_rate": base["identity_match_rate"],
            "briefing_ready": base["briefing_ready"],
            "readiness_rule": "Brief runs only if campaigns Ready/Partial, leads Ready, telephony Ready/Partial, appointments Ready, identity match >=80%."}


@app.get("/api/evaluation")
async def evaluate():
    return evaluation.run_fixtures()


# ----------------------------------------------------------------------------
# Interventions (CP-05 proof-based closure)
# ----------------------------------------------------------------------------
def _hydrate(it):
    leaks = {l["leakage_id"]: l for l in engine.build_leakages()}
    l = leaks.get(it["leakage_id"])
    it["leakage"] = {k: l.get(k) for k in ("type", "region", "clinic_code", "severity", "stage",
                     "opportunity_relationship", "recoverable_appointments", "recoverable_value_inr")} if l else None
    it["owner"] = engine.OWNER_BY_ID.get(it.get("owner_id"))
    it["allowed_transitions"] = [s for s in TRANSITIONS.get(it["status"], []) if s not in PATCH_BLOCKED]
    it["can_claim_proof"] = it["status"] == "Proof Required"
    it["can_verify"] = it["status"] == "Closure Claimed"
    return it


@app.get("/api/interventions")
async def list_interventions(session_id: str = Depends(get_session)):
    await ensure_session_seed(session_id)
    items = [_hydrate(i) for i in await repo.list(session_id)]
    return {"interventions": items, "session_id": session_id, "state_machine": TRANSITIONS}


@app.post("/api/interventions")
async def create_intervention(req: InterventionCreate, session_id: str = Depends(get_session)):
    await ensure_session_seed(session_id)
    leaks = {l["leakage_id"]: l for l in engine.build_leakages()}
    l = leaks.get(req.leakage_id)
    if not l:
        raise HTTPException(404, "Leakage not found")
    if req.owner_id and req.owner_id not in OWNER_IDS:
        raise HTTPException(422, "unknown owner")
    existing = await repo.find_by_leakage(session_id, req.leakage_id)
    if existing:
        return existing
    return await repo.create(session_id, l, req.owner_id, req.due_date, req.title)


async def _get_intervention(intervention_id, session_id):
    doc = await repo.find(session_id, intervention_id)
    if not doc:
        raise HTTPException(404, "Intervention not found")
    return doc


@app.patch("/api/interventions/{intervention_id}")
async def update_intervention(intervention_id: str, req: InterventionUpdate,
                              session_id: str = Depends(get_session)):
    doc = await _get_intervention(intervention_id, session_id)
    update = {}
    if req.status:
        if req.status in PATCH_BLOCKED:
            raise HTTPException(409, f"'{req.status}' requires the proof/verify workflow, not a direct status change.")
        if req.status not in TRANSITIONS.get(doc["status"], []):
            raise HTTPException(409, f"Invalid transition {doc['status']} -> {req.status}.")
        update["status"] = req.status
    if req.owner_id is not None:
        update["owner_id"] = req.owner_id or None
        if not update.get("status") and doc["status"] == "Detected" and req.owner_id:
            update["status"] = "Assigned"
    if req.due_date is not None:
        update["due_date"] = req.due_date
    history = doc.get("history", [])
    history.append({"at": _now_iso(), "event": "updated",
                    "status": update.get("status", doc["status"]), "note": req.note})
    update["history"] = history
    if req.note:
        notes = doc.get("notes", [])
        notes.append({"at": _now_iso(), "text": req.note})
        update["notes"] = notes
    await repo.save(session_id, intervention_id, update)
    return _clean(await _get_intervention(intervention_id, session_id))


@app.post("/api/interventions/{intervention_id}/proof")
async def claim_closure(intervention_id: str, req: ProofClaim, session_id: str = Depends(get_session)):
    doc = await _get_intervention(intervention_id, session_id)
    if doc["status"] != "Proof Required":
        raise HTTPException(409, "Closure can only be claimed from 'Proof Required'.")
    if req.consecutive_days < REQUIRED_CONSECUTIVE_DAYS:
        raise HTTPException(422, f"Proof requires at least {REQUIRED_CONSECUTIVE_DAYS} consecutive days of recovery.")
    if not req.evidence_ids:
        raise HTTPException(422, "Proof requires at least one supporting evidence ID.")
    proof = await repo.create_proof(session_id, {
        "intervention_id": intervention_id, "leakage_id": doc["leakage_id"],
        "metric_id": req.metric_id, "metric_evidence_id": req.metric_evidence_id,
        "observed_before": req.observed_before, "observed_after": req.observed_after,
        "threshold": req.threshold, "window_start": req.window_start, "window_end": req.window_end,
        "consecutive_days": req.consecutive_days, "evidence_ids": req.evidence_ids,
        "note": req.note, "claimed_at": _now_iso(), "verification": None,
    })
    history = doc.get("history", [])
    history.append({"at": _now_iso(), "event": "closure_claimed", "status": "Closure Claimed",
                    "proof_id": proof["proof_id"]})
    await repo.save(session_id, intervention_id,
                    {"status": "Closure Claimed", "proof_id": proof["proof_id"], "history": history})
    return {"intervention": _clean(await _get_intervention(intervention_id, session_id)),
            "proof": proof}


@app.post("/api/interventions/{intervention_id}/verify")
async def verify_closure(intervention_id: str, req: VerifyRequest, session_id: str = Depends(get_session)):
    doc = await _get_intervention(intervention_id, session_id)
    if doc["status"] != "Closure Claimed":
        raise HTTPException(409, "Only a 'Closure Claimed' intervention can be verified.")
    if not doc.get("proof_id"):
        raise HTTPException(409, "No proof record to verify.")
    verification = {"verified_by": req.verified_by or "reviewer",
                    "verified_at": _now_iso(), "decision": req.decision, "note": req.note}
    await repo.save_proof(session_id, doc["proof_id"], {"verification": verification})
    new_status = "Closed" if req.decision == "approved" else "Reopened"
    history = doc.get("history", [])
    history.append({"at": _now_iso(), "event": f"verification_{req.decision}", "status": new_status,
                    "note": req.note})
    update = {"status": new_status, "history": history}
    if new_status == "Reopened":
        update["proof_id"] = None
    await repo.save(session_id, intervention_id, update)
    return _clean(await _get_intervention(intervention_id, session_id))


@app.post("/api/interventions/{intervention_id}/close")
async def close_intervention(intervention_id: str, req: CloseRequest,
                             session_id: str = Depends(get_session)):
    """Typed closure (deepening #2; ADR-0003/0004).

    Validates the closure transition via the typed state machine, resolves the
    REQUIRED opportunity_group_ref to a real OpportunityGroup (no orphans),
    applies the doctrine-Q4 sector/company precedence rule, and records an
    immutable ClosureEvent on the append-only spine.
    """
    doc = await _get_intervention(intervention_id, session_id)

    # 1. Typed transition: the substrate status must sit in the closure sub-path
    #    and be allowed to advance to closure_claimed.
    src = intervention_state.FROM_SUBSTRATE.get(doc["status"])
    if src is None:
        raise HTTPException(409, f"Status '{doc['status']}' is not in the closure sub-path.")
    try:
        intervention_state.validate_transition(src, intervention_state.ClosureState.CLOSURE_CLAIMED)
    except intervention_state.InvalidTransition as e:
        raise HTTPException(409, str(e))

    # 2. Resolve the cited OpportunityGroup (no orphan closures).
    if req.region not in REGION_IDS:
        raise HTTPException(422, f"unknown region '{req.region}'")
    groups = cycle_compute.region_groups(req.region, req.sector)
    matched = next((g for g in groups if g.opportunity_group_id == req.opportunity_group_ref), None)
    if matched is None:
        raise HTTPException(422, f"opportunity_group_ref '{req.opportunity_group_ref}' "
                                 f"does not resolve to an OpportunityGroup in {req.region}.")

    # 3. Typed claim, naming the cycle stage and the named actor.
    claim = intervention_state.ClosureClaim(
        stage=matched.stage, named_actor=req.named_actor, evidence_ids=req.evidence_ids,
        consecutive_days=req.consecutive_days, note=req.note,
    )

    # 4. Doctrine Q4: default precedence from the cited group's relationship;
    #    sector wins on conflict unless a named actor overrides.
    default = precedence_from_relationship(matched.opportunity_relationship)
    res = resolve_precedence(req.sector_position, req.company_position, default,
                             override_actor=req.override_actor, override_reason=req.override_reason)

    # 5. Immutable ClosureEvent on the append-only spine.
    event = ClosureEvent(
        closure_id=f"CL-{intervention_id}-{_now_iso()}",
        intervention_id=intervention_id,
        opportunity_group_ref=req.opportunity_group_ref,
        claim=claim.model_dump(),
        proof=None,
        precedence_source=res["precedence_source"],
        overridden_by=res["overridden_by"],
        override_reason=res["override_reason"],
        timestamp=_now_iso(),
        audit_trail=res["audit_trail"],
    )
    event_id = closure_spine.append(event)

    # 6. Advance the substrate status (the spine, not the status flag, is the
    #    source of truth — the status is a projection).
    history = doc.get("history", [])
    history.append({"at": _now_iso(), "event": "closure_event_recorded", "status": "Closure Claimed",
                    "closure_event_id": event_id, "precedence_source": res["precedence_source"]})
    await repo.save(session_id, intervention_id, {"status": "Closure Claimed", "history": history})

    return {
        "intervention": _clean(await _get_intervention(intervention_id, session_id)),
        "closure_event": event.model_dump(),
        "event_id": event_id,
        "conflict": res["conflict"],
    }


# ----------------------------------------------------------------------------
# Session isolation (CP-07)
# ----------------------------------------------------------------------------
@app.post("/api/session/reset")
async def reset_session(session_id: str = Depends(get_session)):
    await repo.reset(session_id)
    await ensure_session_seed(session_id)
    return {"status": "reset", "session_id": session_id}
