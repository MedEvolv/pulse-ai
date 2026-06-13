"""Regional Leakage Briefing Agent.

The model NEVER computes numbers. It receives deterministic facts and returns a
schema-valid, evidence-grounded brief. A deterministic template fallback always
works without a model key.
"""
from __future__ import annotations

import json
import os
import re
from typing import Optional

from dotenv import load_dotenv

import engine

load_dotenv()

PROMPT_VERSION = "brief-1.0.0"
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

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

SYSTEM_MESSAGE = """You are the Regional Leakage Briefing Agent for Pulse AI, a healthcare Revenue Operations tool.
You convert deterministic metrics, leakage objects and evidence references into a concise, role-specific operating brief.

STRICT RULES:
- Cite ONLY evidence IDs that appear in the supplied evidence set. Never invent evidence IDs.
- Never recalculate or invent any metric or number. Use only the numbers given in the facts.
- Never invent causal claims. Distinguish correlation, operational diagnosis and proven cause.
- Never include patient identifiers (names, phones, emails, clinical notes).
- Never recommend autonomous external action (calls, messages, emails, budget changes). Every intervention requires human approval.
- State missing evidence in caveats. Maximum 3 findings, maximum 3 interventions. Each intervention has exactly one owner_role.
- Use concise executive language.
- Be terse: summary at most 2 sentences; each "finding" and "why_it_matters" at most one sentence (~25 words). Output compact JSON only.

Respond with ONLY a valid JSON object, no markdown, matching exactly this schema:
{
  "brief_id": "string",
  "headline": "string",
  "summary": "string",
  "top_findings": [{"finding": "string", "why_it_matters": "string", "metric_ids": ["string"], "evidence_ids": ["string"], "confidence": "high|medium|low"}],
  "recommended_interventions": [{"title": "string", "owner_role": "string", "priority": "high|medium|low", "evidence_ids": ["string"], "human_approval_required": true}],
  "caveats": ["string"],
  "insufficient_evidence": false
}"""


def build_facts(region: str, question: str = "", role: str = "regional_head") -> dict:
    metrics = engine.compute_metrics("current", region)
    prior = engine.compute_metrics("prior", region)
    leaks = engine.leakages_for(region)
    rec = engine.recoverable(region)
    dq = data_quality_summary(region)

    evidence_ids = sorted({e for l in leaks for e in l["evidence_ids"]})
    evidence = [engine.get_evidence_index()[e] for e in evidence_ids if e in engine.get_evidence_index()]
    metric_ids = [
        f"METRIC-CONTACT-{region}", f"METRIC-SHOW-{region}",
        f"METRIC-BOOKING-{region}", f"METRIC-CPA-{region}",
        f"METRIC-SLA-{region}",
    ]
    return {
        "region": {"region_id": region, "name": engine.REGION_NAME.get(region)},
        "date_range": {"start": engine.CURRENT_START.date().isoformat(), "end": engine.REFERENCE_DATE.date().isoformat()},
        "metrics": metrics,
        "prior_metrics": prior,
        "metric_ids": metric_ids,
        "leakages": [{k: l[k] for k in ("leakage_id", "type", "severity", "severity_score",
                                        "metric", "observed", "threshold", "clinic_code",
                                        "recoverable_appointments", "recoverable_value_inr",
                                        "owner_role", "evidence_ids", "confidence")} for l in leaks],
        "recoverable": rec,
        "evidence": evidence,
        "data_quality": dq,
        "requested_question": question,
        "role": role,
    }


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


def _deterministic_brief(facts: dict) -> dict:
    region = facts["region"]
    leaks = facts["leakages"]
    rname = region["name"]

    if not facts["data_quality"]["briefing_ready"]:
        return {
            "brief_id": f"BRIEF-{region['region_id']}-DET",
            "headline": f"Insufficient evidence to brief {rname} Region",
            "summary": "Critical source data is missing or below the identity-match threshold.",
            "top_findings": [], "recommended_interventions": [],
            "caveats": ["Briefing readiness rule not met."],
            "insufficient_evidence": True, "mode": "deterministic",
        }

    top = leaks[:3]
    findings, interventions = [], []
    type_label = {
        "slow_first_contact": "First-contact response is too slow",
        "low_contact_rate": "Contact rate is below the best region",
        "contact_to_booking_drop": "Connected leads are not converting to bookings",
        "high_no_show_rate": "A clinic has an excessive no-show rate",
        "high_cost_per_attended": "Cost per attended appointment is inflated",
        "clinic_concentration": "One clinic concentrates most recoverable loss",
        "repeat_complaint_context": "Repeat complaint context at a clinic",
    }
    for l in top:
        label = type_label.get(l["type"], l["type"])
        scope = f" at clinic {l['clinic_code']}" if l.get("clinic_code") else ""
        findings.append({
            "finding": f"{label}{scope} (observed {l['observed']}, threshold {l['threshold']}).",
            "why_it_matters": f"Estimated {l['recoverable_appointments']} recoverable appointments "
                              f"(~INR {l['recoverable_value_inr']:,}) tied to this {l['severity']} leakage.",
            "metric_ids": [f"METRIC-{l['metric'].upper()}-{region['region_id']}"],
            "evidence_ids": l["evidence_ids"][:4],
            "confidence": l["confidence"],
        })
        interventions.append({
            "title": f"Address {label.lower()}{scope}",
            "owner_role": l["owner_role"],
            "priority": "high" if l["severity"] in ("Critical", "High") else "medium",
            "evidence_ids": l["evidence_ids"][:2],
            "human_approval_required": True,
        })

    headline = (f"{rname} Region is losing paid-search efficiency after lead capture"
                if top else f"{rname} Region shows no material leakage")
    summary = (f"{rname} spend is INR {facts['metrics']['spend_inr']:,} across "
               f"{facts['metrics']['leads']} leads, but only {facts['metrics']['attended']} attended "
               f"appointments. The loss begins after capture, not in spend volume."
               if top else f"{rname} is performing within thresholds across the funnel.")
    return {
        "brief_id": f"BRIEF-{region['region_id']}-DET",
        "headline": headline, "summary": summary,
        "top_findings": findings[:3],
        "recommended_interventions": interventions[:3],
        "caveats": ["Deterministic briefing. First-touch attribution. Estimates, not realized revenue."],
        "insufficient_evidence": False,
        "mode": "deterministic",
    }


def _validate(brief: dict, allowed_evidence: set, allowed_metrics: set) -> bool:
    try:
        if not isinstance(brief.get("top_findings"), list):
            return False
        if len(brief["top_findings"]) > 3 or len(brief.get("recommended_interventions", [])) > 3:
            return False
        text = json.dumps(brief).lower()
        # privacy: reject phone/email-like patterns
        if re.search(r"\b\d{10}\b", text) or re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", text):
            return False
        for f in brief["top_findings"]:
            for e in f.get("evidence_ids", []):
                if e not in allowed_evidence:
                    return False
        for i in brief.get("recommended_interventions", []):
            if not i.get("human_approval_required", False):
                return False
            for e in i.get("evidence_ids", []):
                if e not in allowed_evidence:
                    return False
        return True
    except Exception:
        return False


async def generate_brief(region: str, question: str = "", role: str = "regional_head",
                         use_model: bool = True, facts: Optional[dict] = None) -> dict:
    if facts is None:
        facts = build_facts(region, question, role)
    allowed_evidence = {e["evidence_id"] for e in facts["evidence"]}
    allowed_metrics = set(facts["metric_ids"])

    det = _deterministic_brief(facts)
    if det["insufficient_evidence"]:
        det["fallback_active"] = True
        return det

    if not use_model or not EMERGENT_LLM_KEY:
        det["fallback_active"] = True
        return det

    # Slim payload keeps the model fast (PRD target < 10s).
    slim = {
        "region": facts["region"],
        "metrics": {k: facts["metrics"][k] for k in
                    ("spend_inr", "leads", "contact_rate", "median_first_contact_delay_min",
                     "uncontacted_24h", "booking_rate", "show_rate", "attended",
                     "cost_per_attended_inr")},
        "prior_metrics": {k: facts["prior_metrics"][k] for k in
                          ("contact_rate", "show_rate", "booking_rate", "cost_per_attended_inr")},
        "leakages": facts["leakages"][:5],
        "evidence": [{"evidence_id": e["evidence_id"], "summary": e["summary"]}
                     for e in facts["evidence"][:14]],
        "metric_ids": facts["metric_ids"],
        "recoverable": facts["recoverable"],
    }

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = (
            LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"brief-{region}",
                system_message=SYSTEM_MESSAGE,
            )
            .with_model("anthropic", "claude-sonnet-4-6")
            .with_params(max_tokens=2000)
        )
        user = UserMessage(text=(
            f"Question: {question or SUPPORTED_QUESTIONS[0]}\nRole: {role}\n\n"
            f"FACTS (authoritative, do not recompute):\n{json.dumps(slim, default=str)}\n\n"
            "Produce the brief now as compact pure JSON. Be terse."
        ))
        raw = await chat.send_message(user)
        raw = raw.replace("```json", "").replace("```", "").strip()
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        parsed = json.loads(m.group(0) if m else raw)
        if _validate(parsed, allowed_evidence, allowed_metrics):
            parsed["mode"] = "model"
            parsed["fallback_active"] = False
            parsed.setdefault("insufficient_evidence", False)
            return parsed
    except Exception as e:  # noqa: BLE001
        det["model_error"] = str(e)[:200]

    det["fallback_active"] = True
    return det
