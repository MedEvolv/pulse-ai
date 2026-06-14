# Model synthesis uses Vertex AI Gemini

## Context

ADR-0006 removed Emergent and left the brief model-synthesis path behind a
provider-neutral `_complete()` seam. A provider had to be chosen. Options: the
Anthropic API (Claude), the Gemini API via Google AI Studio (a plain key, free
tier), or **Vertex AI Gemini** on Google Cloud (service-account / express key,
covered by GCP trial credits). The model is only ever asked to narrate
deterministic facts into validated JSON — a small, gated, cached, off-by-default
call — and the strict `validate_brief_output` validator guards the output
regardless of provider.

## Decision

Use **Vertex AI Gemini** (`gemini-2.5-flash` by default) via the unified
`google-genai` SDK, implemented in `briefing.py::_complete()`. Auth:

- **Primary — Vertex express API key**: `LLM_API_KEY` → `genai.Client(vertexai=True, api_key=...)`.
- **Alternative — service account / ADC**: set `GOOGLE_CLOUD_PROJECT` (+ `GOOGLE_CLOUD_LOCATION`, `GOOGLE_APPLICATION_CREDENTIALS`).

`LLM_MODEL` overrides the model id. The SDK is imported lazily, so the
deterministic path carries no LLM dependency.

## Why

- Uses Google Cloud trial credits the estate already has, and aligns with the
  estate's existing GCP-AI-Agent direction.
- **Vertex (unlike the free AI Studio tier) does not train on prompt data** —
  the right posture for when real (non-synthetic) facts eventually flow, matching
  the existing real-data / DPDP gate.
- The provider is swappable: `_complete()` is the only Gemini-specific code, and
  the validator makes any provider's output safe (malformed → deterministic brief).

## Consequences

- `google-genai` added to `requirements.txt`; installed in the deploy but unused
  until credentials are set (model off by default — runtime unchanged today).
- Supersedes ADR-0006's tentative "direct Anthropic" successor note.

## Correction (2026-06-14) — auth method picks the endpoint

The initial assumption of a "Vertex express API key" was **wrong**. Verified live:

- **API key → Vertex AI** fails with `401 UNAUTHENTICATED: API keys are not
  supported by this API`. Vertex requires OAuth2 / a service account.
- **API key → Gemini Developer API** (`generativelanguage`) authenticates, but its
  billing is the separate **AI Studio prepay wallet** — which returned
  `429 RESOURCE_EXHAUSTED: prepayment credits are depleted`. The GCP trial credits
  do **not** apply to the Developer API.
- **Service account → Vertex** (the way to actually spend GCP credits) is blocked
  on this account by org policy `constraints/iam.disableServiceAccountKeyCreation`
  ("Key creation is not allowed") — only an org admin can lift it.

`_genai_client()` now routes by auth method: `GOOGLE_SERVICE_ACCOUNT_JSON` or
`GOOGLE_CLOUD_PROJECT` → Vertex; `LLM_API_KEY` → Gemini Developer API (never Vertex).

**Current state:** live model synthesis is blocked by account/billing constraints,
not code. The deterministic brief is fully functional and is what the demo serves.
Two unblocks, both requiring user/admin action: (i) an org admin disables the SA-key
constraint → service-account + Vertex on GCP credits; or (ii) fund the Gemini
Developer-API billing → the existing API key works. Model stays off until then.
