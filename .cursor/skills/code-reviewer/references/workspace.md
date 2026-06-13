# Review workspace

Transient handoff between agents. Synthesizer may prune after final report.

## Paths

| Context | Workspace root |
|---------|----------------|
| Session-bound | `sessions/<codename>/reviews/workspace/<review-id>/` |
| Ad hoc | `~/.cursor/reviews/workspace/<review-id>/` |

`review-id`: `review-YYYYMMDD-HHMMSS` (orchestrator assigns).

## Layout

```text
<workspace>/
  scope_manifest.json
  findings/
    code-python.json
    code-typescript.json
    docs.json
    intent.json
    tests.json
    leaks.json             # optional (changeset/task hygiene)
    security.json          # optional
    performance.json       # optional
  report.md                # synthesizer output (copy to reviews/ when session-bound)
```

## Session final artifacts

After synthesize, also write:

- `sessions/<codename>/reviews/r-NNN.json` — summary + counts + workspace path
- `sessions/<codename>/progress.json` → `last_review`
- `checkpoints.json` if missing (see [persistence.md](persistence.md))

Ad hoc: optional `~/.cursor/reviews/history/<review-id>/report.md` + `summary.json`.

## Writable

Orchestrator and synthesizer may create workspace dirs and session `reviews/`. Never edit product worktrees.
