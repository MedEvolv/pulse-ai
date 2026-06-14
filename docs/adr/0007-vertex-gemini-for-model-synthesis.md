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
  until `LLM_API_KEY` is set (model off by default — runtime unchanged today).
- Requires GCP setup the repo cannot do: enable the Vertex AI API, create the
  key/service account, set the env vars. Verification of a live call is gated on
  those credentials (tracked in the enablement issue).
- Supersedes ADR-0006's tentative "direct Anthropic" successor note.
