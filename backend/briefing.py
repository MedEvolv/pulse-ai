"""Regional Leakage Briefing Agent (CP-02 + CP-04 compliant).

Deterministic brief is the default. Model synthesis is explicit and validated
with strict Pydantic + provenance + privacy + numeric + confidence checks.
The model never computes numbers; numeric prose is rejected.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Optional

from dotenv import load_dotenv

import engine
from brief_validation import validate_brief_output

load_dotenv()

PROMPT_VERSION = "brief-2.0.0"
# Provider-neutral LLM key (Emergent removed — ADR-0006). When the direct
# Anthropic synthesis path is wired, set LLM_API_KEY to an Anthropic API key.
LLM_API_KEY = os.environ.get("LLM_API_KEY")

SUPPORTED_QUESTIONS = [
    "Why is North Region underperforming?",
    "Which clinics waste the most paid-lead spend?",
    "What changed in appointment show rate?",
    "Who owns the highest-value leakage?",
    "What should the regional head do this week?",
]

INSUFFICIENT_MSG = (
    "This MVP can answer regional leakage, clinic performance, journey, ownership, "
    "and scenario questions. The requested analysis is outside the available evidence."
)

CONFIDENCE_RANK = {"unverified": 0, "low": 1, "medium": 2, "high": 3}

SYSTEM_MESSAGE = """You are the Regional Leakage Briefing Agent for Pulse AI, a healthcare Revenue Operations tool.
You convert deterministic metrics, leakage objects and evidence references into a concise, role-specific operating brief.

STRICT RULES:
- Cite ONLY metric IDs and evidence IDs that appear in the supplied allowlists. Never invent IDs.
- Every finding MUST cite at least one metric ID and one evidence ID (unless insufficient_evidence is true).
- NEVER write any number, digit, percentage or currency amount in prose (headline, summary, finding, why_it_matters, intervention title). Describe direction qualitatively (e.g. "well below benchmark"). The UI renders numbers deterministically.
- Never invent causal claims. Distinguish correlation, operational diagnosis and proven cause.
- Never include patient identifiers (names, phones, emails, clinical notes).
- Never recommend autonomous external action. Every intervention has human_approval_required = true.
- Do not raise confidence above the deterministic confidence ceiling provided in the facts.
- Maximum 3 findings, maximum 3 interventions, one owner_role per intervention.
- Use concise executive language. Be terse.

Respond with ONLY a valid JSON object, no markdown, matching exactly this schema (no extra keys):
{
  "headline": "string",
  "summary": "string",
  "top_findings": [{"finding": "string", "why_it_matters": "string", "metric_ids": ["string"], "evidence_ids": ["string"], "confidence": "high|medium|low|unverified"}],
  "recommended_interventions": [{"title": "string", "owner_role": "regional_head|cluster_operations|telecalling|marketing|finance|customer_success", "priority": "high|medium|low", "evidence_ids": ["string"], "human_approval_required": true}],
  "insufficient_evidence": false,
  "limitations": ["string"]
}"""


def is_supported_question(q: str) -> bool:
    q = (q or "").strip()
    if not q or q in SUPPORTED_QUESTIONS:
        return True
    keywords = ["region", "clinic", "spend", "show", "leak", "owner", "week",
                "underperform", "no-show", "contact", "booking", "appointment", "cost"]
    return any(k in q.lower() for k in keywords)


def bounded_brief() -> dict:
    return {"insufficient_evidence": True, "bounded": True,
            "headline": "Unsupported question",
            "summary": INSUFFICIENT_MSG,
            "top_findings": [], "recommended_interventions": [],
            "limitations": [], "mode": "bounded",
            "fallback_reason_code": "UNSUPPORTED_QUESTION", "evidence_pool": []}


def data_quality_summary(region: Optional[str] = None) -> dict:
    ds = engine.get_dataset("current")

    def cov(records):
        return len(records)

    sources = {
        "campaigns": {"status": "Ready", "records": len(engine.CAMPAIGNS)},
        "leads": {"status": "Ready", "records": cov([l for l in ds["leads"] if not region or l["region_id"] == region])},
        "telephony": {"status": "Partial", "records": cov([a for a in ds["attempts"] if not region or a["region_id"] == region])},
        "appointments": {"status": "Ready", "records": cov([a for a in ds["appointments"] if not region or a["region_id"] == region])},
        "revenue": {"status": "Partial", "records": cov([r for r in ds["revenues"] if not region or r["region_id"] == region])},
        "complaints": {"status": "Ready", "records": cov([r for r in ds["reputations"] if not region or r["region_id"] == region])},
    }
    identity_match_rate = 0.93
    ready = (sources["campaigns"]["status"] in ("Ready", "Partial")
             and sources["leads"]["status"] == "Ready"
             and sources["telephony"]["status"] in ("Ready", "Partial")
             and sources["appointments"]["status"] == "Ready"
             and identity_match_rate >= 0.80)
    return {"sources": sources, "identity_match_rate": identity_match_rate, "briefing_ready": ready}


def deterministic_confidence_ceiling(leaks) -> str:
    best = "low"
    for l in leaks:
        if CONFIDENCE_RANK.get(l["confidence"], 0) > CONFIDENCE_RANK.get(best, 0):
            best = l["confidence"]
    return best


def build_facts(region: str, question: str = "", role: str = "regional_head") -> dict:
    metrics = engine.compute_metrics("current", region)
    prior = engine.compute_metrics("prior", region)
    leaks = engine.leakages_for(region)
    summary = engine.regional_opportunity_summary(region)
    dq = data_quality_summary(region)
    idx = engine.get_evidence_index()

    evidence_ids = sorted({e for l in leaks for e in l["evidence_ids"]})
    evidence = [idx[e] for e in evidence_ids if e in idx]

    metric_ids = sorted({l["metric_id"] for l in leaks if l.get("metric_id")})
    # always expose the three stage metric IDs for the region too
    for stage in ("contact", "booking", "show"):
        metric_ids.append(engine.metric_id_for(stage, region))
    metric_ids = sorted(set(metric_ids))

    return {
        "region": {"region_id": region, "name": engine.REGION_NAME.get(region)},
        "date_range": {"start": engine.CURRENT_START.date().isoformat(),
                       "end": engine.REFERENCE_DATE.date().isoformat()},
        "metrics": metrics,
        "prior_metrics": prior,
        "metric_ids": metric_ids,
        "leakages": [{k: l.get(k) for k in ("leakage_id", "type", "severity", "severity_score",
                      "metric", "metric_id", "observed", "threshold", "clinic_code", "stage",
                      "opportunity_group_id", "opportunity_relationship",
                      "recoverable_appointments", "recoverable_value_inr",
                      "owner_role", "evidence_ids", "confidence")} for l in leaks],
        "opportunity_summary": {k: summary[k] for k in
                                ("unique_opportunity_pools", "related_alerts",
                                 "estimated_attendance_opportunity", "scenario_value_inr")},
        "deterministic_confidence_ceiling": deterministic_confidence_ceiling(leaks),
        "evidence": evidence,
        "data_quality": dq,
        "requested_question": question,
        "role": role,
    }


def allowlists(facts: dict):
    allowed_metric_ids = set(facts["metric_ids"])
    allowed_evidence_ids = {e["evidence_id"] for e in facts["evidence"]}
    return allowed_metric_ids, allowed_evidence_ids


# ---------------------------------------------------------------------------
# Deterministic brief (default, trusted numeric renderer)
# ---------------------------------------------------------------------------
TYPE_LABEL = {
    "slow_first_contact": "First-contact response is too slow",
    "low_contact_rate": "Contact rate is below the best region",
    "contact_to_booking_drop": "Connected leads are not converting to bookings",
    "high_no_show_rate": "A clinic has an excessive no-show rate",
    "high_cost_per_attended": "Cost per attended appointment is inflated (diagnostic)",
    "clinic_concentration": "One clinic concentrates most recoverable loss",
    "repeat_complaint_context": "Repeat complaint context at a clinic",
}


def deterministic_brief(facts: dict, mode: str = "deterministic",
                        reason_code: Optional[str] = None) -> dict:
    region = facts["region"]
    leaks = facts["leakages"]
    rname = region["name"]

    if not facts["data_quality"]["briefing_ready"]:
        return {
            "brief_id": f"BRIEF-{region['region_id']}-DET",
            "headline": f"Insufficient evidence to brief {rname} Region",
            "summary": "Critical source data is missing or below the identity-match threshold.",
            "top_findings": [], "recommended_interventions": [],
            "limitations": ["Briefing readiness rule not met"],
            "insufficient_evidence": True, "mode": "deterministic_fallback",
            "fallback_reason_code": reason_code or "INSUFFICIENT_EVIDENCE",
        }

    top = leaks[:3]
    findings, interventions = [], []
    for l in top:
        label = TYPE_LABEL.get(l["type"], l["type"])
        scope = f" at clinic {l['clinic_code']}" if l.get("clinic_code") else ""
        rel = l.get("opportunity_relationship")
        if rel == "diagnostic":
            why = "Diagnostic signal — investigate; it does not create an independent recovery pool."
        else:
            why = (f"Tied to a {l.get('opportunity_relationship')} opportunity pool "
                   f"({l['recoverable_appointments']} appts, ~INR {l['recoverable_value_inr']:,}). Not additive across related alerts.")
        findings.append({
            "finding": f"{label}{scope}.",
            "why_it_matters": why,
            "metric_ids": [l["metric_id"]] if l.get("metric_id") else [],
            "evidence_ids": l["evidence_ids"][:4],
            "confidence": l["confidence"],
        })
        interventions.append({
            "title": f"Review and act on {label.lower()}{scope}",
            "owner_role": l["owner_role"],
            "priority": "high" if l["severity"] in ("Critical", "High") else "medium",
            "evidence_ids": l["evidence_ids"][:2],
            "human_approval_required": True,
        })

    headline = (f"{rname} Region is losing paid-search efficiency after lead capture"
                if top else f"{rname} Region shows no material leakage")
    summary = (f"{rname} loss begins after capture across {facts['opportunity_summary']['unique_opportunity_pools']} "
               f"unique opportunity pools. Numbers shown are deterministic and non-additive across related alerts."
               if top else f"{rname} is performing within thresholds across the funnel.")
    return {
        "brief_id": f"BRIEF-{region['region_id']}-DET",
        "headline": headline, "summary": summary,
        "top_findings": findings[:3],
        "recommended_interventions": interventions[:3],
        "limitations": ["Deterministic briefing", "First-touch attribution",
                        "Estimates, not realized revenue"],
        "insufficient_evidence": False,
        "mode": mode,
        "fallback_reason_code": reason_code,
    }


# ---------------------------------------------------------------------------
# Model synthesis (explicit, validated)
# ---------------------------------------------------------------------------
async def _complete(system_message: str, user_text: str, max_tokens: int) -> str:
    """Direct LLM completion seam. Emergent removed (ADR-0006).

    The direct Anthropic implementation (claude-sonnet-4-6 via the `anthropic`
    SDK, keyed by LLM_API_KEY) is a tracked follow-up. Until it is wired and
    verified against a real key, this raises NotImplementedError, which
    `synthesize` maps to MODEL_PROVIDER_UNCONFIGURED -> deterministic brief.
    """
    raise NotImplementedError("Direct Anthropic brief synthesis not wired yet")


async def synthesize(facts: dict, question: str, role: str,
                     max_tokens: int = 700, timeout: int = 12):
    """Call the model, validate strictly. Returns (brief_dict, reason_code|None)."""
    det = deterministic_brief(facts)
    if det["insufficient_evidence"]:
        return det, "INSUFFICIENT_EVIDENCE"
    if not LLM_API_KEY:
        return deterministic_brief(facts, "deterministic_fallback", "MODEL_DISABLED"), "MODEL_DISABLED"

    allowed_metric_ids, allowed_evidence_ids = allowlists(facts)
    ceiling = facts["deterministic_confidence_ceiling"]

    slim = {
        "region": facts["region"],
        "metrics": {k: facts["metrics"][k] for k in
                    ("contact_rate", "median_first_contact_delay_min", "booking_rate",
                     "show_rate", "attended", "cost_per_attended_inr")},
        "leakages": [{k: l.get(k) for k in
                      ("type", "severity", "metric_id", "opportunity_relationship",
                       "owner_role", "evidence_ids", "confidence")} for l in facts["leakages"][:5]],
        "allowed_metric_ids": sorted(allowed_metric_ids),
        "allowed_evidence_ids": sorted(allowed_evidence_ids),
        "evidence": [{"evidence_id": e["evidence_id"], "summary": e["summary"]}
                     for e in facts["evidence"][:14]],
        "deterministic_confidence_ceiling": ceiling,
    }

    user_text = (
        f"Question: {question or SUPPORTED_QUESTIONS[0]}\nRole: {role}\n\n"
        f"FACTS (authoritative; cite only the allowlisted IDs; no numbers in prose):\n"
        f"{json.dumps(slim, default=str)}\n\nProduce the brief now as compact pure JSON."
    )
    try:
        raw = await asyncio.wait_for(
            _complete(SYSTEM_MESSAGE, user_text, max_tokens=max_tokens), timeout=timeout)
    except asyncio.TimeoutError:
        return deterministic_brief(facts, "deterministic_fallback", "MODEL_TIMEOUT"), "MODEL_TIMEOUT"
    except NotImplementedError:
        return deterministic_brief(facts, "deterministic_fallback", "MODEL_PROVIDER_UNCONFIGURED"), "MODEL_PROVIDER_UNCONFIGURED"
    except Exception:
        return deterministic_brief(facts, "deterministic_fallback", "MODEL_PROVIDER_ERROR"), "MODEL_PROVIDER_ERROR"

    cleaned = (raw or "").replace("```json", "").replace("```", "").strip()
    m = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not m:
        return deterministic_brief(facts, "deterministic_fallback", "MODEL_OUTPUT_SCHEMA_FAILED"), "MODEL_OUTPUT_SCHEMA_FAILED"
    try:
        parsed = json.loads(m.group(0))
    except Exception:
        return deterministic_brief(facts, "deterministic_fallback", "MODEL_OUTPUT_SCHEMA_FAILED"), "MODEL_OUTPUT_SCHEMA_FAILED"

    ok, reason, clean = validate_brief_output(parsed, allowed_metric_ids, allowed_evidence_ids, ceiling)
    if not ok:
        return deterministic_brief(facts, "deterministic_fallback", reason), reason

    clean["brief_id"] = f"BRIEF-{facts['region']['region_id']}-AI"
    clean["mode"] = "model"
    clean["fallback_reason_code"] = None
    return clean, None
