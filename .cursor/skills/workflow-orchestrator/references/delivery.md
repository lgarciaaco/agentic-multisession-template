# Delivery report

| File | Writer | Role |
|------|--------|------|
| `artifacts/delivery-report.md` | `workflow-write-delivery-report.py` | Final user-facing summary |
| `workflow.json` `phase` | generator | `delivery` → `completed` |

## Generator

```bash
python3 scripts/workflow-write-delivery-report.py <codename>
```

Sources:

- `session.json` — title, tasks (done/pending), `next` hint
- `workflow.json` — loop verdicts
- `artifacts/plan-review/pr-NNN.json` — latest plan review
- `reviews/r-NNN.json` — latest code review

## Resume on `/workflow-orchestrator`

Chat context **Workflow** section includes **Resume** from `workflow_next_action()` — conductor continues that phase without replaying chat history.

## Reopen

| Command | Effect |
|---------|--------|
| `python3 scripts/workflow-reopen-brief.py <codename>` | `brief_accepted` + `plan_user_accepted` false; plan loop reset; `phase: intake` |
| `python3 scripts/workflow-reopen-plan.py <codename>` | `plan_user_accepted` false; `phase: plan_loop` |

## Writable

`sessions/<codename>/artifacts/delivery-report.md`, `workflow.json`. Then `./scripts/sync-session.sh <codename>`.
