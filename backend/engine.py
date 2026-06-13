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

import hashlib
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
RULE_VERSION = "rules-2.0.0"
DATA_VERSION = "data-1.0.0"
PERIOD = "2026-06"
DEFAULT_AVG_REALIZED_VALUE = 17500  # INR per attended -> treatment
IMPACT_DIVISOR = 3800  # tunes recoverable-value -> impact score (0-100)

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
    # Aggregate metric-evidence records (CP-06) participate in the evidence index
    for mev in build_metric_evidence().values():
        idx[mev["evidence_id"]] = {
            "evidence_id": mev["evidence_id"],
            "source_system": "deterministic_metric_engine",
            "source_record_id": mev["metric_id"],
            "summary": (f"{mev['metric_id']}: {mev['numerator']}/{mev['denominator']} "
                        f"= {mev['value']} ({mev['affected_record_count']} affected, {mev['period']})"),
            "region_id": mev["region_id"], "clinic_code": mev["clinic_code"], "lead_id": None,
            "evidence_type": "aggregate_metric",
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
    """Primary funnel ends at Appointment Attended (CP-01.6).

    Treatment/revenue are returned separately as partial contextual data.
    Each stage carries a backend `stage_key` for URL-faithful drilldown (CP-08).
    """
    m = compute_metrics(variant, region)
    stages = [
        ("Leads Captured", "captured", m["leads"]),
        ("Contacted", "contacted", m["contacted"]),
        ("Appointment Booked", "appointment_booked", m["booked"]),
        ("Appointment Attended", "attended", m["attended"]),
    ]
    out = []
    prev = None
    for i, (name, stage_key, count) in enumerate(stages):
        rate = _safe_rate(count, prev) if prev is not None else None
        drop = (prev - count) if prev is not None else 0
        leak = rate is not None and rate < 0.7
        out.append({
            "stage": name, "stage_key": stage_key, "count": count,
            "conversion_rate": rate, "drop": max(drop, 0), "leakage": leak,
        })
        prev = count
    return out


def funnel_context(variant="current", region=None) -> dict:
    """Partial contextual stages (treatment/revenue) — labelled, never part of primary funnel."""
    m = compute_metrics(variant, region)
    return {
        "partial": True,
        "label": "Partial contextual data (separate billing source, not in primary funnel)",
        "treatment_accepted": m["treatments"],
        "revenue_realized_inr": m["revenue_inr"],
    }


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
# CP-01 Economic truth: non-overlapping stage opportunity waterfall
# CP-06 Cohort-faithful aggregate metric evidence
# ----------------------------------------------------------------------------
def clamp01(x):
    if x is None:
        return 0.0
    return max(0.0, min(1.0, x))


def display_round(x):
    """Single shared rounding function for opportunity appointment counts."""
    return int(round(x or 0))


def _cohort_hash(lead_ids):
    h = hashlib.sha256("|".join(sorted(lead_ids)).encode()).hexdigest()
    return f"sha256:{h[:32]}"


STAGE_METRIC = {
    "contact": "CONTACT-RATE",
    "booking": "BOOKING-RATE",
    "show": "SHOW-RATE",
}


def metric_id_for(stage, region, clinic=None):
    suffix = f"-{clinic}" if clinic else ""
    return f"METRIC-{STAGE_METRIC[stage]}-{region}{suffix}-{PERIOD}"


def mev_id_for(stage, region, clinic=None):
    suffix = f"-{clinic}" if clinic else ""
    return f"MEV-{region}{suffix}-{stage.upper()}-{PERIOD}"


@lru_cache(maxsize=1)
def build_metric_evidence() -> dict:
    """One aggregate MetricEvidence record per stage per region (CP-06)."""
    ds = get_dataset("current")
    out: dict[str, dict] = {}
    for region in REGION_DEFS:
        rid = region["region_id"]
        leads = [l for l in ds["leads"] if l["region_id"] == rid]
        connected = [l for l in leads if l["connected"]]
        booked = [l for l in leads if l["booked"]]
        lead_ids = {l["lead_id"] for l in leads}
        appts = [a for a in ds["appointments"] if a["lead_id"] in lead_ids]
        attended = [a for a in appts if a["status"] == "attended"]

        stage_defs = [
            ("contact", len(connected), len(leads),
             [l["lead_id"] for l in leads if not l["connected"]]),
            ("booking", len(booked), len(connected),
             [l["lead_id"] for l in connected if not l["booked"]]),
            ("show", len(attended), len(appts),
             [a["lead_id"] for a in appts if a["status"] != "attended"]),
        ]
        for stage, num, den, affected in stage_defs:
            eid = mev_id_for(stage, rid)
            value = round(num / den, 4) if den else None
            out[eid] = {
                "evidence_id": eid,
                "evidence_type": "aggregate_metric",
                "metric_id": metric_id_for(stage, rid),
                "region_id": rid,
                "clinic_code": None,
                "period": PERIOD,
                "stage": stage,
                "numerator": num,
                "denominator": den,
                "value": value,
                "source_batch_ids": ["BATCH-CRM-2026-06", "BATCH-TEL-2026-06", "BATCH-APT-2026-06"],
                "cohort_definition": {"region_id": rid, "created_period": PERIOD},
                "cohort_hash": _cohort_hash([l["lead_id"] for l in leads]),
                "affected_record_count": len(affected),
                "sample_affected_record_ids": affected[:8],
                "limitations": ["Synthetic data", "First-touch attribution"],
            }
    return out


def benchmark_rates() -> dict:
    bc = best_benchmark("contact_rate")
    bb = best_benchmark("booking_rate")
    bs = best_benchmark("show_rate")
    return {
        "contact": {"type": "best_comparable_region", "source_id": bc["region_id"],
                    "source_name": bc["region"], "value": bc["value"], "period": PERIOD,
                    "caveat": "Best comparable synthetic region for the same period."},
        "booking": {"type": "best_comparable_region", "source_id": bb["region_id"],
                    "source_name": bb["region"], "value": bb["value"], "period": PERIOD,
                    "caveat": "Best comparable synthetic region for the same period."},
        "show": {"type": "best_comparable_region", "source_id": bs["region_id"],
                 "source_name": bs["region"], "value": bs["value"], "period": PERIOD,
                 "caveat": "Best comparable synthetic region for the same period."},
    }


@lru_cache(maxsize=8)
def region_opportunity_groups(region: str, avg_value: float = DEFAULT_AVG_REALIZED_VALUE) -> list:
    """Non-overlapping stage opportunity groups for a region (the only additive pools)."""
    m = compute_metrics("current", region)
    L = m["leads"]
    C, B, S = clamp01(m["contact_rate"]), clamp01(m["booking_rate"]), clamp01(m["show_rate"])
    bench = benchmark_rates()
    Cb = clamp01(bench["contact"]["value"])
    Bb = clamp01(bench["booking"]["value"])
    Sb = clamp01(bench["show"]["value"])

    raws = {
        "contact": L * max(0.0, Cb - C) * B * S,
        "booking": L * Cb * max(0.0, Bb - B) * S,
        "show": L * Cb * Bb * max(0.0, Sb - S),
    }
    cur = {"contact": C, "booking": B, "show": S}
    benchv = {"contact": Cb, "booking": Bb, "show": Sb}
    groups = []
    for stage in ("contact", "booking", "show"):
        raw = raws[stage]
        if raw <= 0.01:
            continue
        disp = display_round(raw)
        groups.append({
            "opportunity_group_id": f"OPP-{region}-{stage.upper()}-{PERIOD}",
            "region_id": region,
            "clinic_code": None,
            "stage": stage,
            "period": PERIOD,
            "current_rate": round(cur[stage], 4),
            "benchmark_rate": round(benchv[stage], 4),
            "raw_additional_attended": round(raw, 2),
            "display_additional_attended": disp,
            "value_inr": round(disp * avg_value),
            "benchmark": {"type": bench[stage]["type"], "source_id": bench[stage]["source_id"]},
            "metric_evidence_id": mev_id_for(stage, region),
            "is_additive_in_summary": True,
            "caveats": ["Shared opportunity pool",
                        "Not additive with another alert carrying this group ID"],
        })
    return groups


def opportunity_group(region, stage):
    for g in region_opportunity_groups(region):
        if g["stage"] == stage:
            return g
    return None


@lru_cache(maxsize=8)
def clinic_show_allocation(region: str, avg_value: float = DEFAULT_AVG_REALIZED_VALUE) -> dict:
    """Allocate the regional SHOW opportunity across clinics (sub-pools, NON-additive).

    Guarantees sum of clinic allocations never exceeds the regional show opportunity.
    """
    show_group = opportunity_group(region, "show")
    if not show_group:
        return {}
    regional_appts = show_group["display_additional_attended"]
    regional_value = show_group["value_inr"]
    cb = clinic_breakdown(region)
    weights = {c["clinic_code"]: max(0, c["recoverable_appointments"]) for c in cb}
    total_w = sum(weights.values())
    alloc = {}
    if total_w <= 0:
        return {}
    running = 0
    items = sorted(weights.items(), key=lambda kv: kv[1], reverse=True)
    for i, (code, w) in enumerate(items):
        share = w / total_w
        appts = display_round(regional_appts * share)
        # cap so the running total never exceeds the regional pool
        appts = min(appts, regional_appts - running)
        running += appts
        alloc[code] = {
            "opportunity_group_id": f"OPP-{region}-SHOW-{code}-{PERIOD}",
            "region_id": region,
            "clinic_code": code,
            "stage": "show",
            "period": PERIOD,
            "share_of_regional_show": round(share, 4),
            "display_additional_attended": appts,
            "value_inr": round(appts * avg_value),
            "parent_opportunity_group_id": show_group["opportunity_group_id"],
            "is_additive_in_summary": False,
            "metric_evidence_id": mev_id_for("show", region),
            "caveats": ["Allocation of the regional show opportunity",
                        "Non-additive with the regional show pool or other clinic allocations"],
        }
    return alloc


def regional_opportunity_summary(region: str) -> dict:
    """Sum only unique additive opportunity groups (the waterfall)."""
    groups = region_opportunity_groups(region)
    total_appts = sum(g["display_additional_attended"] for g in groups)
    total_value = sum(g["value_inr"] for g in groups)
    leaks = leakages_for(region)
    return {
        "region_id": region,
        "period": PERIOD,
        "unique_opportunity_pools": len(groups),
        "related_alerts": len(leaks),
        "estimated_attendance_opportunity": total_appts,
        "scenario_value_inr": total_value,
        "opportunity_groups": groups,
        "note": ("Scenario opportunity based on explicit benchmark assumptions. "
                 "Not a forecast or causal revenue estimate. Not additive across related alerts."),
    }


def _cohort_evidence_ids(region, clinic=None, predicate=None, limit=4):
    """Evidence IDs faithful to the affected cohort (record-level), not nearby records."""
    ds = get_dataset("current")
    out = []
    for l in ds["leads"]:
        if l["region_id"] != region:
            continue
        if clinic and l["clinic_code"] != clinic:
            continue
        if predicate and not predicate(l):
            continue
        # prefer a real attempt/appointment record belonging to this exact lead
        appt = next((a for a in ds["appointments"] if a["lead_id"] == l["lead_id"]), None)
        att = next((a for a in ds["attempts"] if a["lead_id"] == l["lead_id"]), None)
        if appt:
            out.append(f"EV-{appt['appointment_id']}")
        elif att:
            out.append(f"EV-{att['attempt_id']}")
        if len(out) >= limit:
            break
    return out


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
        # Alerts are never additive in the summary; the waterfall groups are.
        kw.setdefault("is_additive_in_summary", False)
        leakages.append(kw)

    def shared_fields(region, stage, owner_role, confidence):
        """Attach the shared regional opportunity group + metric evidence (CP-01.4)."""
        g = opportunity_group(region, stage)
        mev = mev_id_for(stage, region)
        return {
            "metric_id": metric_id_for(stage, region),
            "metric_evidence_id": mev,
            "opportunity_group_id": g["opportunity_group_id"] if g else None,
            "opportunity_relationship": "shared" if g else "diagnostic",
            "recoverable_appointments": g["display_additional_attended"] if g else 0,
            "recoverable_value_inr": g["value_inr"] if g else 0,
            "benchmark": g["benchmark"] if g else None,
            "owner_role": owner_role,
            "confidence": confidence,
        }

    for region in REGION_DEFS:
        rid = region["region_id"]
        rname = region["name"]
        m = compute_metrics("current", rid)
        bench = benchmark_rates()

        # L-01 Slow first contact -> CONTACT opportunity group
        if (m["median_first_contact_delay_min"] and m["median_first_contact_delay_min"] > 120) or \
           (m["leads"] and m["uncontacted_24h"] / m["leads"] > 0.20):
            dev = min(100, round((m["median_first_contact_delay_min"] or 0) / 3))
            sf = shared_fields(rid, "contact", "cluster_operations", "high")
            sev, label, bd = _severity(_impact(sf["recoverable_value_inr"]), dev, 90, 60)
            ev = [sf["metric_evidence_id"]] + _cohort_evidence_ids(
                rid, predicate=lambda l: (l["first_contact_delay_min"] or 0) > 120)
            add(type="slow_first_contact", region_id=rid, region=rname, scope="region",
                clinic_code=None, stage="contact", stage_label="Contacted",
                metric="median_first_contact_delay_min",
                observed=m["median_first_contact_delay_min"], threshold=120, unit="minutes",
                severity_score=sev, severity=label, severity_breakdown=bd,
                affected_records=_affected_lead_ids(rid, predicate=lambda l: (l["first_contact_delay_min"] or 0) > 120),
                affected_record_count=len(_affected_lead_ids(rid, predicate=lambda l: (l["first_contact_delay_min"] or 0) > 120, limit=10000)),
                evidence_ids=ev,
                caveats=["First-touch attribution", "Synthetic data", "Shared contact opportunity pool — not additive"],
                **sf)

        # L-02 Low contact rate -> CONTACT opportunity group (shares with L-01)
        bench_c = bench["contact"]
        if m["contact_rate"] and bench_c["value"] and (bench_c["value"] - m["contact_rate"]) >= 0.10 and m["leads"] >= 20:
            dev = min(100, round((bench_c["value"] - m["contact_rate"]) * 300))
            sf = shared_fields(rid, "contact", "telecalling", "high")
            sev, label, bd = _severity(_impact(sf["recoverable_value_inr"]), dev, 88, 50)
            ev = [sf["metric_evidence_id"]] + _cohort_evidence_ids(rid, predicate=lambda l: not l["connected"])
            add(type="low_contact_rate", region_id=rid, region=rname, scope="region",
                clinic_code=None, stage="contact", stage_label="Contacted", metric="contact_rate",
                observed=m["contact_rate"], threshold=round(bench_c["value"] - 0.10, 4), unit="rate",
                severity_score=sev, severity=label, severity_breakdown=bd,
                affected_records=_affected_lead_ids(rid, predicate=lambda l: not l["connected"]),
                affected_record_count=len(_affected_lead_ids(rid, predicate=lambda l: not l["connected"], limit=10000)),
                evidence_ids=ev,
                caveats=[f"Benchmark = best region ({bench_c['source_name']}) contact rate",
                         "Shared contact opportunity pool — not additive"],
                **sf)

        # L-03 Contact-to-booking drop -> BOOKING opportunity group
        bench_b = bench["booking"]
        contact_breached = m["contact_rate"] and bench_c["value"] and (bench_c["value"] - m["contact_rate"]) >= 0.10
        if m["booking_rate"] and bench_b["value"] and (bench_b["value"] - m["booking_rate"]) >= 0.12 and not contact_breached:
            dev = min(100, round((bench_b["value"] - m["booking_rate"]) * 250))
            sf = shared_fields(rid, "booking", "cluster_operations", "medium")
            sev, label, bd = _severity(_impact(sf["recoverable_value_inr"]), dev, 85, 45)
            ev = [sf["metric_evidence_id"]] + _cohort_evidence_ids(rid, predicate=lambda l: l["connected"] and not l["booked"])
            add(type="contact_to_booking_drop", region_id=rid, region=rname, scope="region",
                clinic_code=None, stage="booking", stage_label="Appointment Booked", metric="booking_rate",
                observed=m["booking_rate"], threshold=round(bench_b["value"] - 0.12, 4), unit="rate",
                severity_score=sev, severity=label, severity_breakdown=bd,
                affected_records=_affected_lead_ids(rid, predicate=lambda l: l["connected"] and not l["booked"]),
                affected_record_count=len(_affected_lead_ids(rid, predicate=lambda l: l["connected"] and not l["booked"], limit=10000)),
                evidence_ids=ev,
                caveats=[f"Benchmark = best region ({bench_b['source_name']}) booking rate",
                         "Shared booking opportunity pool — not additive"],
                **sf)

        # L-04 High no-show (clinic) -> SHOW allocation sub-pool (non-additive)
        alloc = clinic_show_allocation(rid)
        for c in clinic_breakdown(rid):
            if c["show_rate"] is not None and c["show_rate"] < 0.65 and c["scheduled"] >= 15:
                dev = min(100, round((0.65 - c["show_rate"]) * 250))
                a = alloc.get(c["clinic_code"], {})
                appts = a.get("display_additional_attended", 0)
                value = a.get("value_inr", 0)
                sev, label, bd = _severity(_impact(value), dev, 90, 65)
                ev = [mev_id_for("show", rid)] + _cohort_evidence_ids(
                    rid, c["clinic_code"], predicate=lambda l: l["appointment_status"] == "no_show")
                add(type="high_no_show_rate", region_id=rid, region=rname, scope="clinic",
                    clinic_code=c["clinic_code"], stage="show", stage_label="Appointment Attended", metric="show_rate",
                    observed=c["show_rate"], threshold=0.65, unit="rate",
                    severity_score=sev, severity=label, severity_breakdown=bd,
                    affected_records=_affected_lead_ids(rid, c["clinic_code"], predicate=lambda l: l["appointment_status"] == "no_show"),
                    affected_record_count=c["no_show"],
                    evidence_ids=ev,
                    metric_id=metric_id_for("show", rid), metric_evidence_id=mev_id_for("show", rid),
                    opportunity_group_id=a.get("opportunity_group_id"),
                    opportunity_relationship="allocation",
                    recoverable_appointments=appts, recoverable_value_inr=value,
                    benchmark={"type": bench["show"]["type"], "source_id": bench["show"]["source_id"]},
                    owner_role="cluster_operations", confidence="high",
                    caveats=["Allocation of regional show opportunity — non-additive",
                             "Cancelled appointments excluded from no-show"])

        # L-05 High cost per attended -> DIAGNOSTIC ONLY (no recovery pool)
        others = [compute_metrics("current", r["region_id"])["cost_per_attended_inr"]
                  for r in REGION_DEFS if r["region_id"] != rid]
        others = [o for o in others if o]
        if m["cost_per_attended_inr"] and others and m["attended"] >= 10:
            med = statistics.median(others)
            if m["cost_per_attended_inr"] > 1.35 * med:
                dev = min(100, round((m["cost_per_attended_inr"] / med - 1) * 80))
                excess_cost = round((m["cost_per_attended_inr"] - med) * m["attended"])
                sev, label, bd = _severity(min(100, round(excess_cost / 3000)), dev, 92, 55)
                add(type="high_cost_per_attended", region_id=rid, region=rname, scope="region",
                    clinic_code=None, stage="attended", stage_label="Appointment Attended",
                    metric="cost_per_attended_inr",
                    observed=m["cost_per_attended_inr"], threshold=round(1.35 * med), unit="inr",
                    severity_score=sev, severity=label, severity_breakdown=bd,
                    affected_records=[],
                    affected_record_count=m["attended"],
                    evidence_ids=[f"EV-{c['campaign_id']}" for c in CAMPAIGNS if c["region_id"] == rid],
                    metric_id=f"METRIC-CPA-{rid}-{PERIOD}", metric_evidence_id=None,
                    opportunity_group_id=None, opportunity_relationship="diagnostic",
                    recoverable_appointments=0, recoverable_value_inr=0,
                    excess_cost_inr=excess_cost,
                    benchmark={"type": "comparable_region_median", "source_id": None},
                    owner_role="regional_head", confidence="high",
                    caveats=["Diagnostic, not additive — creates no recoverable pool",
                             "First-touch campaign attribution", "Comparable-region median used"])

        # L-06 Clinic concentration -> references the SAME clinic show allocation group as no-show
        cb = clinic_breakdown(rid)
        total_rec = sum(c["recoverable_appointments"] for c in cb)
        if total_rec:
            for c in cb:
                share = c["recoverable_appointments"] / total_rec
                if share > 0.35 and c["recoverable_appointments"] >= 4:
                    dev = min(100, round(share * 120))
                    a = alloc.get(c["clinic_code"], {})
                    value = a.get("value_inr", 0)
                    appts = a.get("display_additional_attended", 0)
                    sev, label, bd = _severity(_impact(value), dev, 80, 55)
                    add(type="clinic_concentration", region_id=rid, region=rname, scope="clinic",
                        clinic_code=c["clinic_code"], stage="show", stage_label="Appointment Attended",
                        metric="recoverable_share",
                        observed=round(share, 4), threshold=0.35, unit="rate",
                        severity_score=sev, severity=label, severity_breakdown=bd,
                        affected_records=_affected_lead_ids(rid, c["clinic_code"]),
                        affected_record_count=c["scheduled"],
                        evidence_ids=[mev_id_for("show", rid)] + _cohort_evidence_ids(rid, c["clinic_code"]),
                        metric_id=metric_id_for("show", rid), metric_evidence_id=mev_id_for("show", rid),
                        opportunity_group_id=a.get("opportunity_group_id"),
                        opportunity_relationship="allocation",
                        recoverable_appointments=appts, recoverable_value_inr=value,
                        benchmark={"type": bench["show"]["type"], "source_id": bench["show"]["source_id"]},
                        owner_role="regional_head", confidence="medium",
                        caveats=["Shares the clinic show pool with the no-show alert — non-additive"])
                    break

        # L-08 Reputation context -> diagnostic/contextual only
        ds = get_dataset("current")
        rep_breached = {}
        for rp in ds["reputations"]:
            if rp["region_id"] == rid and rp["sla_state"] == "breached":
                rep_breached[rp["clinic_code"]] = rep_breached.get(rp["clinic_code"], 0) + 1
        for code, cnt in rep_breached.items():
            if cnt >= 3:
                sev, label, bd = _severity(35, 40, 60, 30)
                add(type="repeat_complaint_context", region_id=rid, region=rname, scope="clinic",
                    clinic_code=code, stage="attended", stage_label="Appointment Attended",
                    metric="breached_sla_count",
                    observed=cnt, threshold=3, unit="count",
                    severity_score=sev, severity=label, severity_breakdown=bd,
                    affected_records=[], affected_record_count=cnt,
                    evidence_ids=_evidence_for(rid, code, kinds=("rep",)),
                    metric_id=None, metric_evidence_id=None,
                    opportunity_group_id=None, opportunity_relationship="diagnostic",
                    recoverable_appointments=0, recoverable_value_inr=0,
                    benchmark=None,
                    owner_role="cluster_operations", confidence="low",
                    caveats=["Contextual signal only — NOT the proven cause of acquisition leakage"])
                break

    leakages.sort(key=lambda x: x["severity_score"], reverse=True)
    return leakages


def leakages_for(region=None):
    out = build_leakages()
    if region:
        out = [l for l in out if l["region_id"] == region]
    return out

