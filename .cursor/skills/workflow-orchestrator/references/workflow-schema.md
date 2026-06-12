# workflow.json schema

Canonical path: `sessions/<codename>/workflow.json`. Created when user runs `/workflow-orchestrator`; resume reads this file first.

## Top-level fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | integer | yes | Schema version; currently `2` |
| `phase` | string | yes | Current pipeline phase (see phases below) |
| `gates` | object | yes | Human gate booleans |
| `loops` | object | yes | Autonomous loop counters |
| `artifacts` | object | yes | Repo-relative paths under `sessions/<codename>/` |

## phases

| Value | Meaning |
|-------|---------|
| `intake` | Analyst interviewing user |
| `brief_review` | Brief drafted; awaiting user accept |
| `plan_loop` | Autonomous plan author ↔ reviewer |
| `plan_user_review` | Plan APPROVED internally; user gate — conductor presents **refused dispositions only** |
| `implementation` | Parent agent implements action plan |
| `code_review_loop` | Autonomous code review |
| `pr_creation` | Commit and open draft PR (auto after code review PASS) |
| `ci_observe` | Poll CI, rebase on conflict, fix on failure (auto loop) |
| `delivery` | Writing delivery report |
| `completed` | Pipeline finished |

## gates

| Field | Type | Set when |
|-------|------|----------|
| `brief_accepted` | boolean | User `accept brief` or correlated inbox at `brief_review` |
| `plan_user_accepted` | boolean | User `accept plan` or correlated inbox at `plan_user_review` |
| `inbox.last_pull_at` | string \| null | ISO timestamp of last inbox gate pull |
| `inbox.processed_markers` | string[] | Hashes of inbox blocks already applied or surfaced at a gate |

## loops.plan

| Field | Type | Description |
|-------|------|-------------|
| `iteration` | integer | Current loop count (0 before first run) |
| `max` | integer | Escalate after this many iterations (default 5) |
| `last_verdict` | string \| null | `APPROVE`, `REVISE`, `REJECT`, or null |

## loops.implementation

| Field | Type | Description |
|-------|------|-------------|
| `active_task` | string | Task id for current PR slice (e.g. `t1`) |
| `ready_for_review` | boolean | Conductor set when coding complete; triggers code review |

## loops.code_review

| Field | Type | Description |
|-------|------|-------------|
| `iteration` | integer | Current code review loop count |
| `max` | integer | Default 5 |
| `last_verdict` | string \| null | `PASS`, `INCOMPLETE`, `FAIL`, or null |
| `task_id` | string \| null | Task under review for this slice |

## loops.pr_creation

| Field | Type | Description |
|-------|------|-------------|
| `iteration` | integer | Current PR creation attempt count |
| `max` | integer | Default 5 |
| `last_verdict` | string \| null | `SUCCESS`, `RETRY`, `FAIL`, or null |

## loops.ci_observe

| Field | Type | Description |
|-------|------|-------------|
| `iteration` | integer | Current CI observe loop count |
| `max` | integer | Default 5 |
| `last_verdict` | string \| null | `GREEN`, `CONFLICT`, `TEST_FAILURE`, `TIMEOUT`, or null |

## artifacts

| Key | Default path | Purpose |
|-----|--------------|---------|
| `brief` | `artifacts/problem-brief.md` | Problem brief |
| `plan` | `artifacts/action-plan.md` | Action plan |
| `delivery` | `artifacts/delivery-report.md` | Final report |
| `plan_feedback` | `artifacts/plan-feedback.md` | User notes at plan gate (optional) |
| `code_review_disposition` | `artifacts/code-review-disposition.md` | Fixer SUGGESTION/NIT dispositions |

## Example

See [sessions/_template/workflow.json](../../../../sessions/_template/workflow.json).

## Writable

Conductor updates `phase`, `gates`, `loops` after each transition. `./scripts/sync-session.sh <codename>` refreshes chat context.

## New sessions

`create_session_tree()` does **not** copy `workflow.json` or `artifacts/` — workflow is opt-in via `/workflow-orchestrator` bootstrap (see SKILL.md). Template files live under `sessions/_template/` for manual or conductor copy.
