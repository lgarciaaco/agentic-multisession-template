# Plan review persistence

| File | Writer | Role |
|------|--------|------|
| `reviews/workspace/wf-*/` | conductor + Task agents | transient handoff |
| `artifacts/plan-review/pr-NNN.json` | plan synthesizer | append-only summary |
| `artifacts/plan-review/pr-NNN-report.md` | plan synthesizer | human report |
| `workflow.json` `loops.plan` | conductor | iteration + last_verdict |

## pr-NNN.json

```json
{
  "id": "pr-001",
  "at": "2026-06-09T12:00:00+00:00",
  "workflow_id": "wf-20260609-120000",
  "workspace": "sessions/alpha/reviews/workspace/wf-20260609-120000-iter1",
  "verdict": "REVISE",
  "findings_count": {"required": 1, "suggestion": 0, "nit": 0}
}
```

## Helper script

```bash
python3 scripts/workflow-plan-synthesize.py <codename> <workspace-relative-to-hub-root>
```

Reads `<workspace>/findings/plan.json`, persists pr-NNN, updates `workflow.json`.

## Writable

`sessions/<codename>/artifacts/plan-review/`, `workflow.json`. Then `./scripts/sync-session.sh <codename>`.
