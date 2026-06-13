"""CP-02: Strict evidence-bound briefing contract + validators.

Validates the FULL model output (schema, provenance, privacy, numeric, confidence,
action-boundary). On any failure the caller discards the model output and uses the
deterministic brief with a bounded reason code. No raw exception text is surfaced.
"""
from __future__ import annotations

import re
from typing import List, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, ValidationError

CONFIDENCE_RANK = {"unverified": 0, "low": 1, "medium": 2, "high": 3}

OWNER_ROLES = ("regional_head", "cluster_operations", "telecalling",
               "marketing", "finance", "customer_success")

FORBIDDEN_KEYS = {"name", "full_name", "patient_name", "phone", "mobile", "email",
                  "address", "dob", "date_of_birth", "aadhaar", "patient", "person_name"}

ALLOWED_OPERATIONAL_KEYS = {"campaign_name", "clinic_name", "region_name", "metric_name"}

EMAIL_RE = re.compile(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", re.I)
# Indian mobile incl. +91 and grouped/spaced/hyphenated variants
MOBILE_RE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")
# Aadhaar-like: 12 digits, optionally grouped 4-4-4 with spaces/hyphens
AADHAAR_RE = re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)")


class BriefFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    finding: str = Field(max_length=240)
    why_it_matters: str = Field(max_length=350)
    metric_ids: List[str] = Field(max_length=3)
    evidence_ids: List[str] = Field(max_length=4)
    confidence: Literal["high", "medium", "low", "unverified"]


class BriefIntervention(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(max_length=180)
    owner_role: Literal["regional_head", "cluster_operations", "telecalling",
                        "marketing", "finance", "customer_success"]
    priority: Literal["high", "medium", "low"]
    evidence_ids: List[str] = Field(max_length=4)
    human_approval_required: Literal[True]


class BriefOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    headline: str = Field(max_length=140)
    summary: str = Field(max_length=700)
    top_findings: List[BriefFinding] = Field(max_length=3)
    recommended_interventions: List[BriefIntervention] = Field(max_length=3)
    insufficient_evidence: bool
    limitations: List[str] = Field(default_factory=list, max_length=8)


def _normalise_digits(text: str) -> str:
    return re.sub(r"[\s\-()]", "", text or "")


def _privacy_scan(obj) -> bool:
    """Return True if PII is detected anywhere in the nested structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            kn = str(k).strip().lower()
            if kn in FORBIDDEN_KEYS and kn not in ALLOWED_OPERATIONAL_KEYS:
                return True
            if _privacy_scan(v):
                return True
        return False
    if isinstance(obj, (list, tuple)):
        return any(_privacy_scan(x) for x in obj)
    if isinstance(obj, str):
        if EMAIL_RE.search(obj):
            return True
        if MOBILE_RE.search(obj):
            return True
        if AADHAAR_RE.search(obj):
            return True
    return False


def _strip_ids(text: str, allowed_ids) -> str:
    out = text or ""
    for tok in sorted(allowed_ids, key=len, reverse=True):
        out = out.replace(tok, " ")
    return out


def _has_ungrounded_number(text: str, allowed_ids) -> bool:
    return bool(re.search(r"\d", _strip_ids(text, allowed_ids)))


def validate_brief_output(
    raw_obj: dict,
    allowed_metric_ids: set,
    allowed_evidence_ids: set,
    confidence_ceiling: str = "high",
) -> Tuple[bool, Optional[str], Optional[dict]]:
    """Validate a model response. Returns (accepted, reason_code, clean_dict)."""
    # 0. Privacy on the raw object first (keys + nested values)
    if _privacy_scan(raw_obj):
        return False, "MODEL_OUTPUT_PRIVACY_FAILED", None

    # 1. Schema (extra keys, invalid confidence, oversized strings/arrays,
    #    human_approval_required must be True)
    try:
        model = BriefOutput(**raw_obj)
    except ValidationError:
        return False, "MODEL_OUTPUT_SCHEMA_FAILED", None

    allowed_ids = set(allowed_metric_ids) | set(allowed_evidence_ids)
    ceiling = CONFIDENCE_RANK.get(confidence_ceiling, 3)

    if not model.insufficient_evidence:
        if not model.top_findings:
            return False, "MODEL_OUTPUT_PROVENANCE_FAILED", None
        for f in model.top_findings:
            # 2. Provenance: non-empty + every ID in the exact allowlist
            if not f.metric_ids or not f.evidence_ids:
                return False, "MODEL_OUTPUT_PROVENANCE_FAILED", None
            for mid in f.metric_ids:
                if mid not in allowed_metric_ids:
                    return False, "MODEL_OUTPUT_PROVENANCE_FAILED", None
            for eid in f.evidence_ids:
                if eid not in allowed_evidence_ids:
                    return False, "MODEL_OUTPUT_PROVENANCE_FAILED", None
            # 3. Confidence ceiling (no escalation above deterministic facts)
            if CONFIDENCE_RANK.get(f.confidence, 3) > ceiling:
                return False, "MODEL_OUTPUT_PROVENANCE_FAILED", None

    for iv in model.recommended_interventions:
        if not iv.evidence_ids:
            return False, "MODEL_OUTPUT_PROVENANCE_FAILED", None
        for eid in iv.evidence_ids:
            if eid not in allowed_evidence_ids:
                return False, "MODEL_OUTPUT_PROVENANCE_FAILED", None

    # 4. Numeric: no ungrounded numbers in business prose
    prose_fields = [model.headline, model.summary]
    for f in model.top_findings:
        prose_fields += [f.finding, f.why_it_matters]
    for iv in model.recommended_interventions:
        prose_fields.append(iv.title)
    for text in prose_fields:
        if _has_ungrounded_number(text, allowed_ids):
            return False, "MODEL_OUTPUT_NUMERIC_FAILED", None

    return True, None, model.model_dump()
