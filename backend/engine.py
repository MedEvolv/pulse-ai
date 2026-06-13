"""
Pulse AI - Deterministic Revenue Operations Engine.

This module is the SINGLE SOURCE OF TRUTH for the application:
  * Deterministic synthetic data generation (fixed seed, no runtime randomness).
  * Metric selectors (spend, contact rate, booking rate, show rate, CPA...).
  * Leakage detection rules + deterministic severity scoring.
  * Evidence index used to ground the AI briefing.

The LLM never computes numbers. It only narrates facts produced here.
"""
from __future__ import annotations

import random
import statistics
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional

IST = timezone(timedelta(hours=5, minutes=30))
REFERENCE_DATE = datetime(2026, 6, 13, 9, 0, tzinfo=IST)
CURRENT_START = REFERENCE_DATE - timedelta(days=30)
PRIOR_START = REFERENCE_DATE - timedelta(days=60)
SEED = 42
RULE_VERSION = "rules-1.0.0"
DATA_VERSION = "data-1.0.0"
DEFAULT_AVG_REALIZED_VALUE = 17500  # INR per attended -> treatment

# ----------------------------------------------------------------------------
# Reference catalogues
# ----------------------------------------------------------------------------
REGION_DEFS = [
    {"region_id": "REG-NORTH", "name": "North"},
    {"region_id": "REG-WEST", "name": "West"},
    {"region_id": "REG-SOUTH", "name": "South"},
]

CLINICS = [
    {"clinic_code": "DL-KMN-01", "name": "Kamla Nagar", "region_id": "REG-NORTH", "weight": 0.25},
    {"clinic_code": "DL-RHN-02", "name": "Rohini", "region_id": "REG-NORTH", "weight": 0.40},
    {"clinic_code": "DL-DWK-03", "name": "Dwarka", "region_id": "REG-NORTH", "weight": 0.20},
    {"clinic_code": "DL-NOD-04", "name": "Noida Sector 62", "region_id": "REG-NORTH", "weight": 0.15},
    {"clinic_code": "MH-BAN-01", "name": "Bandra", "region_id": "REG-WEST", "weight": 0.30},
    {"clinic_code": "MH-AND-02", "name": "Andheri", "region_id": "REG-WEST", "weight": 0.25},
    {"clinic_code": "MH-THN-03", "name": "Thane", "region_id": "REG-WEST", "weight": 0.25},
    {"clinic_code": "MH-PUN-04", "name": "Pune Kothrud", "region_id": "REG-WEST", "weight": 0.20},
    {"clinic_code": "KA-IND-01", "name": "Indiranagar", "region_id": "REG-SOUTH", "weight": 0.30},
    {"clinic_code": "KA-WFD-02", "name": "Whitefield", "region_id": "REG-SOUTH", "weight": 0.25},
    {"clinic_code": "KA-JAY-03", "name": "Jayanagar", "region_id": "REG-SOUTH", "weight": 0.25},
    {"clinic_code": "KA-HSR-04", "name": "HSR Layout", "region_id": "REG-SOUTH", "weight": 0.20},
]

CAMPAIGNS = [
    {"campaign_id": "CMP-GGL-NORTH-01", "platform": "google", "campaign_name": "North Search Implant", "region_id": "REG-NORTH", "spend_inr": 240000, "weight": 3},
    {"campaign_id": "CMP-MET-NORTH-02", "platform": "meta", "campaign_name": "North Social Smile", "region_id": "REG-NORTH", "spend_inr": 90000, "weight": 1},
    {"campaign_id": "CMP-GGL-WEST-01", "platform": "google", "campaign_name": "West Search Implant", "region_id": "REG-WEST", "spend_inr": 150000, "weight": 2},
    {"campaign_id": "CMP-MET-WEST-02", "platform": "meta", "campaign_name": "West Social Smile", "region_id": "REG-WEST", "spend_inr": 70000, "weight": 1},
    {"campaign_id": "CMP-GGL-SOUTH-01", "platform": "google", "campaign_name": "South Search Implant", "region_id": "REG-SOUTH", "spend_inr": 130000, "weight": 2},
    {"campaign_id": "CMP-MET-SOUTH-02", "platform": "meta", "campaign_name": "South Social Smile", "region_id": "REG-SOUTH", "spend_inr": 60000, "weight": 1},
]

OWNERS = [
    {"owner_id": "OWNER-NEHA", "name": "Neha Sharma", "role": "cluster_operations"},
    {"owner_id": "OWNER-VIKRAM", "name": "Vikram Nair", "role": "telecalling"},
    {"owner_id": "OWNER-ROHAN", "name": "Rohan Iyer", "role": "revops_analyst"},
    {"owner_id": "OWNER-ANANYA", "name": "Ananya Mehra", "role": "regional_head"},
    {"owner_id": "OWNER-PRIYA", "name": "Priya Deshmukh", "role": "cluster_operations"},
]

# Per-region behavioural parameters used by the generator.
PERIOD_PARAMS = {
    "current": {
        "REG-NORTH": {"leads": 110, "contact_rate": 0.55, "slow_rate": 0.55, "uncontacted24_rate": 0.18, "booking_rate": 0.62, "show_rate": 0.66},
        "REG-WEST": {"leads": 65, "contact_rate": 0.88, "slow_rate": 0.12, "uncontacted24_rate": 0.03, "booking_rate": 0.70, "show_rate": 0.82},
        "REG-SOUTH": {"leads": 65, "contact_rate": 0.82, "slow_rate": 0.20, "uncontacted24_rate": 0.05, "booking_rate": 0.46, "show_rate": 0.75},
    },
    "prior": {
        "REG-NORTH": {"leads": 95, "contact_rate": 0.69, "slow_rate": 0.30, "uncontacted24_rate": 0.07, "booking_rate": 0.66, "show_rate": 0.76},
        "REG-WEST": {"leads": 60, "contact_rate": 0.87, "slow_rate": 0.13, "uncontacted24_rate": 0.03, "booking_rate": 0.69, "show_rate": 0.81},
        "REG-SOUTH": {"leads": 60, "contact_rate": 0.81, "slow_rate": 0.18, "uncontacted24_rate": 0.05, "booking_rate": 0.55, "show_rate": 0.76},
    },
}

CLINIC_SHOW_OVERRIDE = {"DL-RHN-02": 0.42}  # Rohini = high no-show clinic

REGION_NAME = {r["region_id"]: r["name"] for r in REGION_DEFS}
CLINIC_BY_CODE = {c["clinic_code"]: c for c in CLINICS}
CAMPAIGN_BY_ID = {c["campaign_id"]: c for c in CAMPAIGNS}
OWNER_BY_ID = {o["owner_id"]: o for o in OWNERS}


def _iso(dt: datetime) -> str:
    return dt.isoformat()


# ----------------------------------------------------------------------------
# Deterministic data generation
# ----------------------------------------------------------------------------
def _build_dataset(variant: str) -> dict:
    rng = random.Random(SEED if variant == "current" else SEED + 7)
    params = PERIOD_PARAMS[variant]
    window_start = CURRENT_START if variant == "current" else PRIOR_START
    pfx = "" if variant == "current" else "P"

    clinics_by_region: dict[str, list] = {}
    for c in CLINICS:
        clinics_by_region.setdefault(c["region_id"], []).append(c)
    camps_by_region: dict[str, list] = {}
    for c in CAMPAIGNS:
        camps_by_region.setdefault(c["region_id"], []).append(c)

    leads, attempts, appointments, revenues, reputations = [], [], [], [], []
    lead_n = call_n = apt_n = rev_n = rep_n = 0

    for region in REGION_DEFS:
        rid = region["region_id"]
        p = params[rid]
        rclinics = clinics_by_region[rid]
        cl_weights = [c["weight"] for c in rclinics]
        rcamps = camps_by_region[rid]
        cmp_weights = [c["weight"] for c in rcamps]

        for _ in range(p["leads"]):
            lead_n += 1
            lead_id = f"LEAD-{pfx}{lead_n:04d}"
            clinic = rng.choices(rclinics, weights=cl_weights)[0]
            campaign = rng.choices(rcamps, weights=cmp_weights)[0]
            created = window_start + timedelta(
                minutes=rng.randint(0, 30 * 24 * 60 - 6 * 60)
            )

            connected = rng.random() < p["contact_rate"]
            slow = rng.random() < p["slow_rate"]
            no_attempt_24h = rng.random() < p["uncontacted24_rate"]

            lead_attempts = []
            if no_attempt_24h:
                first_delay = rng.randint(24 * 60 + 60, 40 * 60)
                connected = False
            elif slow:
                first_delay = rng.randint(125, 600)
            else:
                first_delay = rng.randint(3, 28)

            n_attempts = rng.randint(1, 2) if connected else rng.randint(1, 3)
            for ai in range(n_attempts):
                call_n += 1
                attempted_at = created + timedelta(
                    minutes=first_delay + ai * rng.randint(30, 240)
                )
                if ai == n_attempts - 1 and connected:
                    outcome = "connected"
                else:
                    outcome = rng.choice(["no_answer", "busy", "not_connected"])
                att = {
                    "attempt_id": f"CALL-{pfx}{call_n:04d}",
                    "lead_id": lead_id,
                    "attempted_at": _iso(attempted_at),
                    "outcome": outcome,
                    "duration_seconds": rng.randint(120, 300) if outcome == "connected" else 0,
                    "owner_id": rng.choice(["OWNER-NEHA", "OWNER-VIKRAM", "OWNER-PRIYA"]),
                    "source_system": "telephony_export",
                    "source_record_id": f"TEL-{pfx}{50000 + call_n}",
                    "ingest_batch_id": "BATCH-DEMO-003",
                    "region_id": rid,
                    "clinic_code": clinic["clinic_code"],
                }
                lead_attempts.append(att)
            attempts.extend(lead_attempts)

            booked = connected and rng.random() < p["booking_rate"]
            appt = None
            lead_status = "captured"
            if connected:
                lead_status = "contacted"
            if booked:
                apt_n += 1
                show_rate = CLINIC_SHOW_OVERRIDE.get(clinic["clinic_code"], p["show_rate"])
                r = rng.random()
                if r < show_rate:
                    status = "attended"
                elif r < show_rate + 0.12:
                    status = "cancelled"
                else:
                    status = "no_show"
                booked_at = created + timedelta(minutes=first_delay + 10)
                scheduled = booked_at + timedelta(days=rng.randint(1, 5), hours=rng.randint(0, 8))
                appt = {
                    "appointment_id": f"APT-{pfx}{apt_n:04d}",
                    "lead_id": lead_id,
                    "clinic_code": clinic["clinic_code"],
                    "region_id": rid,
                    "campaign_id": campaign["campaign_id"],
                    "scheduled_for": _iso(scheduled),
                    "booked_at": _iso(booked_at),
                    "status": status,
                    "source_system": "appointment_export",
                    "source_record_id": f"APT-SRC-{pfx}{apt_n:04d}",
                    "ingest_batch_id": "BATCH-DEMO-004",
                }
                appointments.append(appt)
                lead_status = "appointment_booked"
                if status == "attended":
                    lead_status = "attended"
                    if rng.random() < 0.62:
                        rev_n += 1
                        gross = rng.choice([16000, 18000, 22000, 26000, 30000])
                        revenues.append({
                            "revenue_id": f"REV-{pfx}{rev_n:04d}",
                            "lead_id": lead_id,
                            "clinic_code": clinic["clinic_code"],
                            "region_id": rid,
                            "campaign_id": campaign["campaign_id"],
                            "realized_at": _iso(scheduled + timedelta(days=rng.randint(0, 4))),
                            "gross_value_inr": gross,
                            "net_value_inr": int(gross * 0.92),
                            "status": "realized",
                            "source_system": "billing_export",
                            "source_record_id": f"INV-{pfx}{rev_n:04d}",
                            "ingest_batch_id": "BATCH-DEMO-005",
                        })
                        lead_status = "treatment_accepted"

            first_delay_real = first_delay if lead_attempts else None
            leads.append({
                "lead_id": lead_id,
                "pseudonymous_person_id": f"PERSON-{pfx}{lead_n:04d}",
                "campaign_id": campaign["campaign_id"],
                "channel": campaign["platform"],
                "region_id": rid,
                "clinic_code": clinic["clinic_code"],
                "created_at": _iso(created),
                "lead_status": lead_status,
                "connected": connected,
                "booked": booked,
                "appointment_status": appt["status"] if appt else None,
                "first_contact_delay_min": first_delay_real,
                "no_attempt_24h": no_attempt_24h,
                "source_system": "crm_export",
                "source_record_id": f"CRM-{pfx}{10000 + lead_n}",
                "ingest_batch_id": "BATCH-DEMO-002",
            })

    # Reputation / NPS context (current only). Weight Rohini for complaint theme.
    if variant == "current":
        rep_targets = (
            ["DL-RHN-02"] * 6
            + ["DL-KMN-01", "DL-DWK-03", "KA-WFD-02", "MH-AND-02", "KA-IND-01"] * 2
            + ["MH-BAN-01", "DL-NOD-04", "KA-JAY-03", "MH-THN-03"]
        )
        themes = ["appointment_delay", "callback_delay", "billing_query", "wait_time"]
        for code in rep_targets[:26]:
            rep_n += 1
            breached = code == "DL-RHN-02" or rng.random() < 0.4
            reputations.append({
                "reputation_event_id": f"REP-{rep_n:04d}",
                "clinic_code": code,
                "region_id": CLINIC_BY_CODE[code]["region_id"],
                "event_type": "complaint" if rng.random() < 0.7 else "nps_detractor",
                "theme": "appointment_delay" if code == "DL-RHN-02" else rng.choice(themes),
                "sla_state": "breached" if breached else "met",
                "closure_state": rng.choice(["proof_required", "closed", "open"]),
                "source_system": "reputationos_export",
                "source_record_id": f"TKT-{rep_n:04d}",
                "ingest_batch_id": "BATCH-DEMO-006",
            })

    return {
        "variant": variant,
        "leads": leads,
        "attempts": attempts,
        "appointments": appointments,
        "revenues": revenues,
        "reputations": reputations,
    }


@lru_cache(maxsize=2)
def get_dataset(variant: str = "current") -> dict:
    return _build_dataset(variant)


# ----------------------------------------------------------------------------
# Evidence index
# ----------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_evidence_index() -> dict:
    ds = get_dataset("current")
    idx: dict[str, dict] = {}
    for c in CAMPAIGNS:
        eid = f"EV-{c['campaign_id']}"
        idx[eid] = {
            "evidence_id": eid, "source_system": "marketing_export",
            "source_record_id": c["campaign_id"],
            "summary": f"{c['campaign_name']} ({c['platform']}) spend INR {c['spend_inr']:,}",
            "region_id": c["region_id"], "clinic_code": None, "lead_id": None,
        }
    for a in ds["attempts"]:
        eid = f"EV-{a['attempt_id']}"
        idx[eid] = {
            "evidence_id": eid, "source_system": a["source_system"],
            "source_record_id": a["source_record_id"],
            "summary": f"Contact attempt on {a['lead_id']} outcome={a['outcome']}",
            "region_id": a["region_id"], "clinic_code": a["clinic_code"], "lead_id": a["lead_id"],
        }
    for ap in ds["appointments"]:
        eid = f"EV-{ap['appointment_id']}"
        idx[eid] = {
            "evidence_id": eid, "source_system": ap["source_system"],
            "source_record_id": ap["source_record_id"],
            "summary": f"Appointment {ap['appointment_id']} clinic={ap['clinic_code']} status={ap['status']}",
            "region_id": ap["region_id"], "clinic_code": ap["clinic_code"], "lead_id": ap["lead_id"],
        }
    for rp in ds["reputations"]:
        eid = f"EV-{rp['reputation_event_id']}"
        idx[eid] = {
            "evidence_id": eid, "source_system": rp["source_system"],
            "source_record_id": rp["source_record_id"],
            "summary": f"Reputation {rp['event_type']} theme={rp['theme']} sla={rp['sla_state']}",
            "region_id": rp["region_id"], "clinic_code": rp["clinic_code"], "lead_id": None,
        }
    return idx


# ----------------------------------------------------------------------------
# Metric selectors
# ----------------------------------------------------------------------------
def _filter_leads(ds, region=None, clinic=None):
    out = ds["leads"]
    if region:
        out = [l for l in out if l["region_id"] == region]
    if clinic:
        out = [l for l in out if l["clinic_code"] == clinic]
    return out


def _safe_rate(num, den):
    if not den:
        return None
    return round(num / den, 4)


def compute_metrics(variant="current", region=None, clinic=None) -> dict:
    ds = get_dataset(variant)
    leads = _filter_leads(ds, region, clinic)
    lead_ids = {l["lead_id"] for l in leads}

    appts = [a for a in ds["appointments"] if a["lead_id"] in lead_ids]
    revs = [r for r in ds["revenues"] if r["lead_id"] in lead_ids]

    # Spend from campaigns in scope
    if region:
        spend = sum(c["spend_inr"] for c in CAMPAIGNS if c["region_id"] == region)
    else:
        spend = sum(c["spend_inr"] for c in CAMPAIGNS)

    n_leads = len(leads)
    connected_leads = [l for l in leads if l["connected"]]
    booked_leads = [l for l in leads if l["booked"]]
    delays = [l["first_contact_delay_min"] for l in leads if l["first_contact_delay_min"] is not None]
    no_24h = [l for l in leads if l["no_attempt_24h"]]

    scheduled = [a for a in appts]
    attended = [a for a in appts if a["status"] == "attended"]
    no_show = [a for a in appts if a["status"] == "no_show"]
    cancelled = [a for a in appts if a["status"] == "cancelled"]

    contact_rate = _safe_rate(len(connected_leads), n_leads)
    booking_rate = _safe_rate(len(booked_leads), len(connected_leads))
    show_rate = _safe_rate(len(attended), len(scheduled))
    cpl = round(spend / n_leads) if n_leads else None
    cpa = round(spend / len(attended)) if attended else None
    median_delay = round(statistics.median(delays)) if delays else None

    return {
        "spend_inr": spend,
        "leads": n_leads,
        "cpl_inr": cpl,
        "contacted": len(connected_leads),
        "contact_rate": contact_rate,
        "median_first_contact_delay_min": median_delay,
        "uncontacted_24h": len(no_24h),
        "booked": len(booked_leads),
        "booking_rate": booking_rate,
        "scheduled": len(scheduled),
        "attended": len(attended),
        "no_show": len(no_show),
        "cancelled": len(cancelled),
        "show_rate": show_rate,
        "cost_per_attended_inr": cpa,
        "treatments": len(revs),
        "revenue_inr": sum(r["net_value_inr"] for r in revs),
    }


def funnel(variant="current", region=None) -> list:
    m = compute_metrics(variant, region)
    stages = [
        ("Leads Captured", m["leads"]),
        ("Contacted", m["contacted"]),
        ("Appointment Booked", m["booked"]),
        ("Appointment Attended", m["attended"]),
        ("Treatment Accepted", m["treatments"]),
        ("Revenue Realized", len([1 for _ in range(m["treatments"])])),
    ]
    out = []
    prev = None
    for i, (name, count) in enumerate(stages):
        rate = _safe_rate(count, prev) if prev is not None else None
        drop = (prev - count) if prev is not None else 0
        leak = False
        if rate is not None and rate < 0.7 and i <= 4:
            leak = True
        out.append({
            "stage": name, "count": count,
            "conversion_rate": rate, "drop": max(drop, 0),
            "leakage": leak,
        })
        prev = count
    return out


def best_benchmark(metric_key: str) -> dict:
    """Best-performing region value for a metric (used as recovery benchmark)."""
    best = None
    for r in REGION_DEFS:
        m = compute_metrics("current", r["region_id"])
        v = m.get(metric_key)
        if v is None:
            continue
        if metric_key == "cost_per_attended_inr":
            cond = best is None or v < best["value"]
        else:
            cond = best is None or v > best["value"]
        if cond:
            best = {"region_id": r["region_id"], "region": r["name"], "value": v}
    return best or {"region_id": None, "region": None, "value": None}


def recoverable(region: str, avg_value: float = DEFAULT_AVG_REALIZED_VALUE) -> dict:
    m = compute_metrics("current", region)
    bench_show = best_benchmark("show_rate")
    bench_contact = best_benchmark("contact_rate")
    expected_attended = round(m["scheduled"] * bench_show["value"]) if bench_show["value"] else m["attended"]
    rec_appts = max(0, expected_attended - m["attended"])
    return {
        "recoverable_appointments": rec_appts,
        "recoverable_value_inr": round(rec_appts * avg_value),
        "benchmark_show_rate": bench_show,
        "benchmark_contact_rate": bench_contact,
        "avg_realized_value_inr": avg_value,
    }


def clinic_breakdown(region: str) -> list:
    out = []
    for c in CLINICS:
        if c["region_id"] != region:
            continue
        m = compute_metrics("current", region, c["clinic_code"])
        rec = recoverable_clinic(region, c["clinic_code"])
        out.append({
            "clinic_code": c["clinic_code"], "name": c["name"],
            "leads": m["leads"], "contact_rate": m["contact_rate"],
            "booking_rate": m["booking_rate"], "show_rate": m["show_rate"],
            "scheduled": m["scheduled"], "attended": m["attended"],
            "no_show": m["no_show"],
            "recoverable_appointments": rec,
        })
    return out


def recoverable_clinic(region, clinic):
    m = compute_metrics("current", region, clinic)
    bench_show = best_benchmark("show_rate")
    expected = round(m["scheduled"] * bench_show["value"]) if bench_show["value"] else m["attended"]
    return max(0, expected - m["attended"])


# ----------------------------------------------------------------------------
# Leakage detection
# ----------------------------------------------------------------------------
SEVERITY_WEIGHTS = {"impact": 0.45, "deviation": 0.30, "confidence": 0.15, "ownership": 0.10}


def _impact(recoverable_value_inr):
    """Impact score (0-100) scaled from estimated recoverable value."""
    return min(100, round((recoverable_value_inr or 0) / 2200))


def _severity(impact, deviation, confidence, ownership):
    score = (impact * SEVERITY_WEIGHTS["impact"] + deviation * SEVERITY_WEIGHTS["deviation"]
             + confidence * SEVERITY_WEIGHTS["confidence"] + ownership * SEVERITY_WEIGHTS["ownership"])
    score = round(score, 1)
    if score >= 85:
        label = "Critical"
    elif score >= 70:
        label = "High"
    elif score >= 45:
        label = "Medium"
    else:
        label = "Low"
    return score, label, {
        "impact_score": impact, "deviation_score": deviation,
        "confidence_score": confidence, "ownership_urgency_score": ownership,
    }


def _evidence_for(region=None, clinic=None, kinds=("attempt", "appt"), limit=6):
    idx = get_evidence_index()
    out = []
    for eid, ev in idx.items():
        if region and ev["region_id"] != region:
            continue
        if clinic and ev["clinic_code"] != clinic:
            continue
        if "attempt" in kinds and eid.startswith("EV-CALL"):
            out.append(eid)
        elif "appt" in kinds and eid.startswith("EV-APT"):
            out.append(eid)
        elif "rep" in kinds and eid.startswith("EV-REP"):
            out.append(eid)
        elif "campaign" in kinds and eid.startswith("EV-CMP"):
            out.append(eid)
        if len(out) >= limit:
            break
    return out


def _affected_lead_ids(region, clinic=None, predicate=None, limit=40):
    ds = get_dataset("current")
    out = []
    for l in ds["leads"]:
        if l["region_id"] != region:
            continue
        if clinic and l["clinic_code"] != clinic:
            continue
        if predicate and not predicate(l):
            continue
        out.append(l["lead_id"])
        if len(out) >= limit:
            break
    return out


@lru_cache(maxsize=1)
def build_leakages() -> list:
    leakages = []
    seq = 0

    def add(**kw):
        nonlocal seq
        seq += 1
        kw["leakage_id"] = f"LEAK-{seq:03d}"
        leakages.append(kw)

    for region in REGION_DEFS:
        rid = region["region_id"]
        rname = region["name"]
        m = compute_metrics("current", rid)
        rec = recoverable(rid)

        # L-01 Slow first contact
        if (m["median_first_contact_delay_min"] and m["median_first_contact_delay_min"] > 120) or \
           (m["leads"] and m["uncontacted_24h"] / m["leads"] > 0.20):
            dev = min(100, round((m["median_first_contact_delay_min"] or 0) / 3))
            sev, label, bd = _severity(_impact(rec["recoverable_value_inr"]), dev, 90, 60)
            add(type="slow_first_contact", region_id=rid, region=rname, scope="region",
                clinic_code=None, stage="Contacted", metric="median_first_contact_delay_min",
                observed=m["median_first_contact_delay_min"], threshold=120, unit="minutes",
                severity_score=sev, severity=label, severity_breakdown=bd,
                affected_records=_affected_lead_ids(rid, predicate=lambda l: (l["first_contact_delay_min"] or 0) > 120),
                evidence_ids=_evidence_for(rid, kinds=("attempt",)),
                recoverable_appointments=rec["recoverable_appointments"],
                recoverable_value_inr=rec["recoverable_value_inr"],
                owner_role="cluster_operations", confidence="high",
                caveats=["First-touch attribution. Delay measured from CRM lead-created timestamp."])

        # L-02 Low contact rate
        bench_c = best_benchmark("contact_rate")
        if m["contact_rate"] and bench_c["value"] and (bench_c["value"] - m["contact_rate"]) >= 0.10 and m["leads"] >= 20:
            dev = min(100, round((bench_c["value"] - m["contact_rate"]) * 300))
            sev, label, bd = _severity(_impact(rec["recoverable_value_inr"]), dev, 88, 50)
            add(type="low_contact_rate", region_id=rid, region=rname, scope="region",
                clinic_code=None, stage="Contacted", metric="contact_rate",
                observed=m["contact_rate"], threshold=round(bench_c["value"] - 0.10, 4), unit="rate",
                severity_score=sev, severity=label, severity_breakdown=bd,
                affected_records=_affected_lead_ids(rid, predicate=lambda l: not l["connected"]),
                evidence_ids=_evidence_for(rid, kinds=("attempt",)),
                recoverable_appointments=rec["recoverable_appointments"],
                recoverable_value_inr=rec["recoverable_value_inr"],
                owner_role="telecalling", confidence="high",
                caveats=[f"Benchmark = best region ({bench_c['region']}) contact rate."])

        # L-03 Contact-to-booking drop
        bench_b = best_benchmark("booking_rate")
        contact_breached = m["contact_rate"] and bench_c["value"] and (bench_c["value"] - m["contact_rate"]) >= 0.10
        if m["booking_rate"] and bench_b["value"] and (bench_b["value"] - m["booking_rate"]) >= 0.12 and not contact_breached:
            dev = min(100, round((bench_b["value"] - m["booking_rate"]) * 250))
            sev, label, bd = _severity(_impact(rec["recoverable_value_inr"]), dev, 85, 45)
            add(type="contact_to_booking_drop", region_id=rid, region=rname, scope="region",
                clinic_code=None, stage="Appointment Booked", metric="booking_rate",
                observed=m["booking_rate"], threshold=round(bench_b["value"] - 0.12, 4), unit="rate",
                severity_score=sev, severity=label, severity_breakdown=bd,
                affected_records=_affected_lead_ids(rid, predicate=lambda l: l["connected"] and not l["booked"]),
                evidence_ids=_evidence_for(rid, kinds=("attempt",)),
                recoverable_appointments=rec["recoverable_appointments"],
                recoverable_value_inr=rec["recoverable_value_inr"],
                owner_role="cluster_operations", confidence="medium",
                caveats=[f"Benchmark = best region ({bench_b['region']}) booking rate."])

        # L-04 High no-show (clinic level)
        for c in clinic_breakdown(rid):
            if c["show_rate"] is not None and c["show_rate"] < 0.65 and c["scheduled"] >= 15:
                dev = min(100, round((0.65 - c["show_rate"]) * 250))
                sev, label, bd = _severity(_impact(round(c["recoverable_appointments"] * DEFAULT_AVG_REALIZED_VALUE)), dev, 90, 65)
                add(type="high_no_show_rate", region_id=rid, region=rname, scope="clinic",
                    clinic_code=c["clinic_code"], stage="Appointment Attended", metric="show_rate",
                    observed=c["show_rate"], threshold=0.65, unit="rate",
                    severity_score=sev, severity=label, severity_breakdown=bd,
                    affected_records=_affected_lead_ids(rid, c["clinic_code"], predicate=lambda l: l["appointment_status"] == "no_show"),
                    evidence_ids=_evidence_for(rid, c["clinic_code"], kinds=("appt",)),
                    recoverable_appointments=c["recoverable_appointments"],
                    recoverable_value_inr=round(c["recoverable_appointments"] * DEFAULT_AVG_REALIZED_VALUE),
                    owner_role="cluster_operations", confidence="high",
                    caveats=["Cancelled appointments excluded from no-show but shown separately."])

        # L-05 High cost per attended
        others = [compute_metrics("current", r["region_id"])["cost_per_attended_inr"]
                  for r in REGION_DEFS if r["region_id"] != rid]
        others = [o for o in others if o]
        if m["cost_per_attended_inr"] and others and m["attended"] >= 10:
            med = statistics.median(others)
            if m["cost_per_attended_inr"] > 1.35 * med:
                dev = min(100, round((m["cost_per_attended_inr"] / med - 1) * 80))
                sev, label, bd = _severity(_impact(rec["recoverable_value_inr"]), dev, 92, 55)
                add(type="high_cost_per_attended", region_id=rid, region=rname, scope="region",
                    clinic_code=None, stage="Appointment Attended", metric="cost_per_attended_inr",
                    observed=m["cost_per_attended_inr"], threshold=round(1.35 * med), unit="inr",
                    severity_score=sev, severity=label, severity_breakdown=bd,
                    affected_records=_affected_lead_ids(rid, predicate=lambda l: l["appointment_status"] in ("no_show", None)),
                    evidence_ids=_evidence_for(rid, kinds=("campaign", "appt")),
                    recoverable_appointments=rec["recoverable_appointments"],
                    recoverable_value_inr=rec["recoverable_value_inr"],
                    owner_role="regional_head", confidence="high",
                    caveats=["First-touch campaign attribution. Comparable-region median used."])

        # L-06 Clinic concentration
        cb = clinic_breakdown(rid)
        total_rec = sum(c["recoverable_appointments"] for c in cb)
        if total_rec:
            for c in cb:
                share = c["recoverable_appointments"] / total_rec
                if share > 0.35 and c["recoverable_appointments"] >= 4:
                    dev = min(100, round(share * 120))
                    sev, label, bd = _severity(_impact(round(c["recoverable_appointments"] * DEFAULT_AVG_REALIZED_VALUE)), dev, 80, 55)
                    add(type="clinic_concentration", region_id=rid, region=rname, scope="clinic",
                        clinic_code=c["clinic_code"], stage="Appointment Attended", metric="recoverable_share",
                        observed=round(share, 4), threshold=0.35, unit="rate",
                        severity_score=sev, severity=label, severity_breakdown=bd,
                        affected_records=_affected_lead_ids(rid, c["clinic_code"]),
                        evidence_ids=_evidence_for(rid, c["clinic_code"], kinds=("appt",)),
                        recoverable_appointments=c["recoverable_appointments"],
                        recoverable_value_inr=round(c["recoverable_appointments"] * DEFAULT_AVG_REALIZED_VALUE),
                        owner_role="regional_head", confidence="medium",
                        caveats=["Concentration measured on estimated recoverable appointments."])
                    break

        # L-08 Reputation context (contextual only)
        ds = get_dataset("current")
        rep_breached = {}
        for rp in ds["reputations"]:
            if rp["region_id"] == rid and rp["sla_state"] == "breached":
                rep_breached[rp["clinic_code"]] = rep_breached.get(rp["clinic_code"], 0) + 1
        for code, cnt in rep_breached.items():
            if cnt >= 3:
                sev, label, bd = _severity(35, 40, 60, 30)
                add(type="repeat_complaint_context", region_id=rid, region=rname, scope="clinic",
                    clinic_code=code, stage="Appointment Attended", metric="breached_sla_count",
                    observed=cnt, threshold=3, unit="count",
                    severity_score=sev, severity=label, severity_breakdown=bd,
                    affected_records=[],
                    evidence_ids=_evidence_for(rid, code, kinds=("rep",)),
                    recoverable_appointments=0, recoverable_value_inr=0,
                    owner_role="cluster_operations", confidence="low",
                    caveats=["Contextual signal only. NOT presented as the proven cause of acquisition leakage."])
                break

    leakages.sort(key=lambda x: x["severity_score"], reverse=True)
    return leakages


def leakages_for(region=None):
    out = build_leakages()
    if region:
        out = [l for l in out if l["region_id"] == region]
    return out
