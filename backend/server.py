"""Pulse AI FastAPI server. All routes are prefixed with /api."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

import briefing
import engine
import evaluation

load_dotenv()

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="Pulse AI")
api = app  # routes declared with /api prefix directly

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_STATUSES = ["New", "Reviewed", "Assigned", "In Progress", "Proof Required", "Closed", "Rejected"]


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------------------
# Intervention seeding & persistence
# ----------------------------------------------------------------------------
async def seed_interventions():
    existing = await db.interventions.count_documents({})
    if existing:
        return
    leaks = engine.build_leakages()
    seeds = []
    defaults = [
        ("OWNER-NEHA", "Assigned", "2026-06-17"),
        ("OWNER-VIKRAM", "In Progress", "2026-06-16"),
        (None, "New", None),
    ]
    for i, l in enumerate(leaks[:6]):
        owner, status, due = defaults[i] if i < len(defaults) else (None, "New", None)
        seeds.append({
            "intervention_id": f"INT-{i+1:04d}",
            "leakage_id": l["leakage_id"],
            "title": f"Remediate {l['type'].replace('_', ' ')} in {l['region']}"
                     + (f" / {l['clinic_code']}" if l.get("clinic_code") else ""),
            "owner_id": owner,
            "status": status,
            "due_date": due,
            "closure_criteria": "Provide proof the metric crossed back over threshold for 5 consecutive days.",
            "external_writeback": False,
            "notes": [],
            "history": [{"at": _now_iso(), "event": "seeded", "status": status}],
        })
    if seeds:
        await db.interventions.insert_many(seeds)


@app.on_event("startup")
async def _startup():
    # warm deterministic caches
    engine.build_leakages()
    await seed_interventions()


def _clean(doc):
    if doc:
        doc.pop("_id", None)
    return doc


# ----------------------------------------------------------------------------
# Request models
# ----------------------------------------------------------------------------
class BriefRequest(BaseModel):
    region: str
    question: Optional[str] = ""
    role: Optional[str] = "regional_head"
    use_model: Optional[bool] = True


class SimRequest(BaseModel):
    region: str
    contact_improve_pp: float = 0
    booking_improve_pp: float = 0
    show_improve_pp: float = 0
    avg_realized_value: float = engine.DEFAULT_AVG_REALIZED_VALUE


class InterventionUpdate(BaseModel):
    status: Optional[str] = None
    owner_id: Optional[str] = None
    due_date: Optional[str] = None
    note: Optional[str] = None


class InterventionCreate(BaseModel):
    leakage_id: str
    title: Optional[str] = None
    owner_id: Optional[str] = None
    due_date: Optional[str] = None


# ----------------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------------
@app.get("/api/health")
async def health():
    return {"status": "ok", "data_version": engine.DATA_VERSION, "rule_version": engine.RULE_VERSION,
            "prompt_version": briefing.PROMPT_VERSION,
            "model_key_present": bool(briefing.EMERGENT_LLM_KEY)}


@app.get("/api/meta")
async def meta():
    return {
        "regions": engine.REGION_DEFS,
        "clinics": engine.CLINICS,
        "campaigns": engine.CAMPAIGNS,
        "owners": engine.OWNERS,
        "reference_date": engine.REFERENCE_DATE.date().isoformat(),
        "date_range": {"start": engine.CURRENT_START.date().isoformat(),
                       "end": engine.REFERENCE_DATE.date().isoformat(), "label": "Last 30 days"},
        "data_version": engine.DATA_VERSION,
        "rule_version": engine.RULE_VERSION,
        "prompt_version": briefing.PROMPT_VERSION,
        "supported_questions": briefing.SUPPORTED_QUESTIONS,
    }


FORMULAS = {
    "spend_inr": "Sum of campaign spend in scope",
    "leads": "Count of valid leads",
    "cpl_inr": "CPL = campaign spend / valid leads",
    "contact_rate": "Unique leads with >=1 connected contact / valid leads",
    "median_first_contact_delay_min": "Median of (first attempt timestamp - lead created)",
    "booking_rate": "Unique leads with booked appointment / unique connected leads",
    "show_rate": "Attended appointments / appointments scheduled",
    "cost_per_attended_inr": "Cost per Attended = campaign spend / attended appointments (first-touch)",
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
        if value <= t["healthy"]:
            return "healthy"
        if value <= t["watch"]:
            return "watch"
        return "breach"
    if value >= t["healthy"]:
        return "healthy"
    if value >= t["watch"]:
        return "watch"
    return "breach"


def _delta(cur, prev):
    if cur is None or prev is None or prev == 0:
        return None
    return round((cur - prev), 4)


@app.get("/api/cockpit")
async def cockpit(region: str = "REG-NORTH"):
    cur = engine.compute_metrics("current", region)
    prev = engine.compute_metrics("prior", region)

    def tile(key, label, fmt="number"):
        return {
            "key": key, "label": label, "format": fmt,
            "value": cur.get(key), "prior": prev.get(key),
            "delta": _delta(cur.get(key), prev.get(key)),
            "state": _state(key, cur.get(key)),
            "formula": FORMULAS.get(key, ""),
        }

    health_strip = [
        tile("spend_inr", "Ad Spend", "inr"),
        tile("leads", "Leads", "number"),
        tile("contact_rate", "Contact Rate", "percent"),
        tile("show_rate", "Show Rate", "percent"),
        tile("cost_per_attended_inr", "Cost / Attended", "inr"),
    ]

    leaks = engine.leakages_for(region)
    inter_map = {i["leakage_id"]: i async for i in db.interventions.find({})}
    top = []
    for l in leaks[:5]:
        iv = inter_map.get(l["leakage_id"])
        top.append({**l,
                    "owner_id": iv["owner_id"] if iv else None,
                    "status": iv["status"] if iv else "New",
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
            "high_severity_leakages": high_leaks,
            "at_risk": high_leaks >= 2,
        })

    return {
        "region": region, "region_name": engine.REGION_NAME.get(region),
        "last_refreshed": _now_iso(),
        "metrics": cur,
        "health_strip": health_strip,
        "funnel": engine.funnel("current", region),
        "top_leakages": top,
        "comparison": comparison,
    }


@app.post("/api/brief")
async def brief(req: BriefRequest):
    q = (req.question or "").strip()
    if q and q not in briefing.SUPPORTED_QUESTIONS:
        # bounded handling: still answer regional leakage questions, else abstain message
        keywords = ["region", "clinic", "spend", "show", "leak", "owner", "week", "underperform", "no-show", "contact", "booking"]
        if not any(k in q.lower() for k in keywords):
            return {"insufficient_evidence": True, "bounded": True,
                    "headline": "Unsupported question",
                    "summary": briefing.INSUFFICIENT_MSG,
                    "top_findings": [], "recommended_interventions": [],
                    "caveats": [], "mode": "bounded", "fallback_active": True,
                    "evidence_pool": []}
    facts = briefing.build_facts(req.region, q, req.role)
    result = await briefing.generate_brief(req.region, q, req.role, req.use_model, facts=facts)
    result["evidence_pool"] = facts["evidence"]
    result["generated_at"] = _now_iso()
    return result


@app.get("/api/leakages")
async def leakages(region: Optional[str] = None):
    leaks = engine.leakages_for(region)
    inter_map = {i["leakage_id"]: i async for i in db.interventions.find({})}
    out = []
    for l in leaks:
        iv = inter_map.get(l["leakage_id"])
        out.append({**l,
                    "owner_id": iv["owner_id"] if iv else None,
                    "status": iv["status"] if iv else "New",
                    "due_date": iv["due_date"] if iv else None,
                    "intervention_id": iv["intervention_id"] if iv else None,
                    "evidence_count": len(l["evidence_ids"])})
    return {"leakages": out}


@app.get("/api/leakages/{leakage_id}")
async def leakage_detail(leakage_id: str):
    leaks = engine.build_leakages()
    l = next((x for x in leaks if x["leakage_id"] == leakage_id), None)
    if not l:
        raise HTTPException(404, "Leakage not found")
    idx = engine.get_evidence_index()
    evidence = [idx[e] for e in l["evidence_ids"] if e in idx]
    iv = await db.interventions.find_one({"leakage_id": leakage_id})
    return {
        "leakage": l,
        "evidence": evidence,
        "intervention": _clean(iv),
        "owner": engine.OWNER_BY_ID.get(iv["owner_id"]) if iv and iv.get("owner_id") else None,
        "clinic": engine.CLINIC_BY_CODE.get(l["clinic_code"]) if l.get("clinic_code") else None,
    }


@app.get("/api/journeys")
async def journeys(region: Optional[str] = None, clinic: Optional[str] = None,
                   channel: Optional[str] = None, campaign: Optional[str] = None,
                   stage: Optional[str] = None, appointment_status: Optional[str] = None,
                   leakage_flag: Optional[str] = None, limit: int = 200):
    ds = engine.get_dataset("current")
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
    return {"total": len(rows), "journeys": rows}


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
            "detail": f"Call outcome: {a['outcome']}",
        })
    for ap in [x for x in ds["appointments"] if x["lead_id"] == lead_id]:
        timeline.append({
            "type": "appointment", "at": ap["booked_at"],
            "source_system": ap["source_system"], "source_record_id": ap["source_record_id"],
            "actor": None, "status": ap["status"], "evidence_id": f"EV-{ap['appointment_id']}",
            "detail": f"Appointment {ap['status']} at {ap['clinic_code']}, scheduled {ap['scheduled_for'][:10]}",
        })
    for r in [x for x in ds["revenues"] if x["lead_id"] == lead_id]:
        timeline.append({
            "type": "revenue", "at": r["realized_at"],
            "source_system": r["source_system"], "source_record_id": r["source_record_id"],
            "actor": None, "status": r["status"], "evidence_id": None,
            "detail": f"Treatment realized net INR {r['net_value_inr']:,}",
        })
    timeline.sort(key=lambda x: x["at"])
    return {"lead": lead, "clinic": engine.CLINIC_BY_CODE.get(lead["clinic_code"]),
            "campaign": engine.CAMPAIGN_BY_ID.get(lead["campaign_id"]), "timeline": timeline}


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
            "cost_per_attended_inr": sim_cpa,
        },
        "assumptions": [
            "Scenario estimate based on current cohort and explicit assumptions.",
            f"Average realized value per attended = INR {round(req.avg_realized_value):,}.",
            "Improvements applied multiplicatively across the funnel. Not a forecast.",
        ],
    }


@app.get("/api/data-quality")
async def data_quality(region: Optional[str] = None):
    base = briefing.data_quality_summary(region)
    ds = engine.get_dataset("current")
    cards = []
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
    for key, src in base["sources"].items():
        d = detail[key]
        cards.append({"key": key, "label": labels[key], "status": src["status"],
                      "records": src["records"], "date_coverage": "Last 30 days", **d})
    return {"sources": cards, "identity_match_rate": base["identity_match_rate"],
            "briefing_ready": base["briefing_ready"],
            "readiness_rule": "Brief runs only if campaigns Ready/Partial, leads Ready, telephony Ready/Partial, appointments Ready, identity match >=80%."}


@app.get("/api/evaluation")
async def evaluate():
    return evaluation.run_fixtures()


@app.get("/api/interventions")
async def list_interventions():
    items = [_clean(i) async for i in db.interventions.find({})]
    leaks = {l["leakage_id"]: l for l in engine.build_leakages()}
    for it in items:
        l = leaks.get(it["leakage_id"])
        it["leakage"] = {k: l[k] for k in ("type", "region", "clinic_code", "severity", "stage",
                                           "recoverable_appointments", "recoverable_value_inr")} if l else None
        it["owner"] = engine.OWNER_BY_ID.get(it.get("owner_id"))
    return {"interventions": items}


@app.post("/api/interventions")
async def create_intervention(req: InterventionCreate):
    leaks = {l["leakage_id"]: l for l in engine.build_leakages()}
    l = leaks.get(req.leakage_id)
    if not l:
        raise HTTPException(404, "Leakage not found")
    existing = await db.interventions.find_one({"leakage_id": req.leakage_id})
    if existing:
        return _clean(existing)
    count = await db.interventions.count_documents({})
    doc = {
        "intervention_id": f"INT-{count+1:04d}",
        "leakage_id": req.leakage_id,
        "title": req.title or f"Remediate {l['type'].replace('_', ' ')} in {l['region']}",
        "owner_id": req.owner_id,
        "status": "Assigned" if req.owner_id else "New",
        "due_date": req.due_date,
        "closure_criteria": "Provide proof the metric crossed back over threshold for 5 consecutive days.",
        "external_writeback": False,
        "notes": [],
        "history": [{"at": _now_iso(), "event": "created", "status": "Assigned" if req.owner_id else "New"}],
    }
    await db.interventions.insert_one(doc)
    return _clean(doc)


@app.patch("/api/interventions/{intervention_id}")
async def update_intervention(intervention_id: str, req: InterventionUpdate):
    doc = await db.interventions.find_one({"intervention_id": intervention_id})
    if not doc:
        raise HTTPException(404, "Intervention not found")
    update = {}
    if req.status:
        if req.status not in ALLOWED_STATUSES:
            raise HTTPException(400, f"Invalid status. Allowed: {ALLOWED_STATUSES}")
        update["status"] = req.status
    if req.owner_id is not None:
        update["owner_id"] = req.owner_id
        if not update.get("status") and doc["status"] == "New":
            update["status"] = "Assigned"
    if req.due_date is not None:
        update["due_date"] = req.due_date
    history = doc.get("history", [])
    history.append({"at": _now_iso(), "event": "updated",
                    "status": update.get("status", doc["status"]),
                    "note": req.note})
    update["history"] = history
    if req.note:
        notes = doc.get("notes", [])
        notes.append({"at": _now_iso(), "text": req.note})
        update["notes"] = notes
    await db.interventions.update_one({"intervention_id": intervention_id}, {"$set": update})
    doc = await db.interventions.find_one({"intervention_id": intervention_id})
    return _clean(doc)
