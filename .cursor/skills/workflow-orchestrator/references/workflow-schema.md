# workflow.json schema

Canonical path: `sessions/<codename>/workflow.json`. Created when user runs `/workflow`; resume reads this file first.

## Top-level fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | integer | yes | Schema version; currently `1` |
| `phase` | string | yes | Current pipeline phase (see phases below) |
| `gates` | object | yes | Human gate booleans |
| `loops` | object | yes | Autonomous loop counters |
| `artifacts` | object | yes | Repo-relative paths under `sessions/<codename>/` |

## phases

| Value | Meaning |
|-------|---------|
| `intake` | Analyst interviewing user |
| `brief_review` | Brief drafted; awaiting user accept |
| `plan_loop` | Autonomous plan author ↔ reviewer (M4) |
| `plan_user_review` | Plan APPROVED internally; user gate |
| `implementation` | Parent agent implements action plan |
| `code_review_loop` | Autonomous code review (M6) |
| `delivery` | Writing delivery report |
| `completed` | Pipeline finished |

## gates

| Field | Type | Set when |
|-------|------|----------|
| `brief_accepted` | boolean | User `accept brief` |
| `plan_user_accepted` | boolean | User `accept plan` |

## loops.plan

| Field | Type | Description |
|-------|------|-------------|
| `iteration` | integer | Current loop count (0 before first run) |
| `max` | integer | Escalate after this many iterations (default 5) |
| `last_verdict` | string \| null | `APPROVE`, `REVISE`, `REJECT`, or null |

## loops.code_review

| Field | Type | Description |
|-------|------|-------------|
| `iteration` | integer | Current code review loop count |
| `max` | integer | Default 5 |
| `last_verdict` | string \| null | `PASS`, `PASS_WITH_NITS`, `INCOMPLETE`, `FAIL`, or null |

## artifacts

| Key | Default path | Purpose |
|-----|--------------|---------|
| `brief` | `artifacts/problem-brief.md` | Problem brief |
| `plan` | `artifacts/action-plan.md` | Action plan |
| `delivery` | `artifacts/delivery-report.md` | Final report |
| `plan_feedback` | `artifacts/plan-feedback.md` | User notes at plan gate (optional) |

## Example

See [sessions/_template/workflow.json](../../../../sessions/_template/workflow.json).

## Writable

Conductor updates `phase`, `gates`, `loops` after each transition. `./scripts/sync-session.sh <codename>` refreshes chat context.

## New sessions

`create_session_tree()` does **not** copy `workflow.json` or `artifacts/` — workflow is opt-in via `/workflow` bootstrap (see SKILL.md). Template files live under `sessions/_template/` for manual or conductor copy.
