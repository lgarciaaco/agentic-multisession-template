# Session persistence

Review workspace is transient — see [workspace.md](workspace.md). Final artifacts persist here.

| File | Writer | Role |
|------|--------|------|
| `reviews/workspace/<review-id>/` | orchestrator + agents | handoff (may prune after synthesize) |
| `reviews/r-NNN.json` | synthesizer | append-only summary |
| `checkpoints.json` | synthesizer | baseline SHAs |
| `progress.json` | synthesizer | `last_review` pointer |

## reviews/r-NNN.json

```json
{
  "id": "r-001",
  "at": "<iso>",
  "review_id": "review-20260608-120000",
  "workspace": "sessions/alpha/reviews/workspace/review-20260608-120000",
  "scope": "full",
  "target": "<path>",
  "verdict": "INCOMPLETE",
  "agents": ["code-python", "docs", "security"],
  "findings_count": {"blocker": 0, "required": 3, "suggestion": 5, "nit": 1}
}
```

## checkpoints.json

Unchanged — auto-capture on first review per [scope-and-delta.md](scope-and-delta.md).

## Writable

`sessions/<codename>/` only for session-bound runs. Then `./scripts/sync-session.sh <codename>`.
