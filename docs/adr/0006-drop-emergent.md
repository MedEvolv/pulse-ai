# Drop the Emergent platform; own the codebase

## Context

Pulse AI was originally generated on the Emergent platform, which left three
couplings: (1) an auto-commit bot that regenerates the app and pushes
"Auto-generated changes" to `main` — a recurring clobber/divergence risk; (2)
`emergentintegrations`, a proprietary LLM wrapper that is not on public PyPI and
repeatedly broke the Vercel build when re-pinned; (3) the model-synthesis path
routed Claude through Emergent's wrapper. Meanwhile the estate's direction
(ADR-0001..0005, the unified-database plan) moves deliberately toward a Supabase
Postgres + repository-seam architecture that Emergent's regenerator works against.

## Decision

Stop using Emergent. The repository is owned and edited directly (Claude Code /
AFK agents against the recorded ADRs), not regenerated. Concretely:

- `emergentintegrations` is removed from the dependencies and the code.
- The brief model-synthesis path is decoupled from Emergent behind a neutral
  `_complete()` seam in `briefing.py`. Its direct **Anthropic** implementation
  (`claude-sonnet-4-6`) is a tracked follow-up; until wired, model mode returns
  `MODEL_PROVIDER_UNCONFIGURED` and the deterministic brief is served (model mode
  is off by default, so runtime behaviour is unchanged).
- The `EMERGENT_LLM_KEY` env var is renamed to the provider-neutral `LLM_API_KEY`.
- The in-repo `.emergent/` marker is deleted.

## Why

The codebase is now architecture-led (recorded decisions, a real test surface, a
repository seam). A generative regenerator that rewrites from its own model is
incompatible with that — it would clobber the seam, reintroduce Mongo +
`emergentintegrations`, and break the Vercel build. The only thing Emergent
uniquely provided was the model call, and that is Claude — reachable directly via
the Anthropic API with no proprietary wrapper.

## Consequences

- The "re-comment `emergentintegrations` before redeploying" hazard is gone.
- Reviving AI synthesis requires wiring the Anthropic SDK + an `LLM_API_KEY`
  (tracked separately); the demo stays deterministic until then.
- **Platform action (not in this repo):** the Emergent integration must be
  disconnected on the Emergent side so its bot stops pushing to `main`. Deleting
  `.emergent/` here does not do that.
