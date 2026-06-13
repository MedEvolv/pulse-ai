# Issue tracker: GitHub

Issues and PRDs for this repo live as GitHub issues on `MedEvolv/pulse-ai`. Use the `gh`
CLI for all operations.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

Infer the repo from `git remote -v` — `gh` does this automatically when run inside a clone.

## When a skill says "publish to the issue tracker"

Create a GitHub issue.

## When a skill says "fetch the relevant ticket"

Run `gh issue view <number> --comments`.

## Repo-specific notes

- The vault (`01_Projects/ReputationOps_Mirror`) and `AGENT.md` remain the canonical
  product memory. GitHub issues are for discrete, grabbable units of work — not the
  strategic record.
- An Emergent-platform bot auto-commits to `main`. Prefer feature branches for
  issue-scoped work and always `git fetch` before committing (see `AGENT.md` §32).
