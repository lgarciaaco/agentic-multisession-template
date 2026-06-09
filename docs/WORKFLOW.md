# Workflow orchestrator walkthrough

Single-session pipeline: **Problem → Plan → Code → Review**. One Cursor chat, three user gates.

## Prerequisites

- Hub bound to a session codename (`./scripts/resolve-session.sh`)
- Optional product repos in `repos.yaml` for worktree implementation

## 1. Start

```bash
./scripts/resolve-session.sh          # must print codename
```

In chat: **`/workflow`**

Conductor bootstraps `workflow.json` + `artifacts/` from `sessions/_template/` if missing.

## 2. Gate 1 — Problem brief

| Phase | You do | Agent does |
|-------|--------|------------|
| `intake` | Answer analyst questions | Draft `artifacts/problem-brief.md` |
| `brief_review` | **`accept brief`** | Sets `gates.brief_accepted`; enters plan loop |

Reopen: `python3 scripts/workflow-reopen-brief.py <codename>`

## 3. Autonomous plan loop (no relay)

Phase `plan_loop` — agent runs without asking you to forward messages:

1. Task(plan-author) → `artifacts/action-plan.md`
2. Task(plan-reviewer) → `findings/plan.json`
3. `python3 scripts/workflow-plan-synthesize.py <codename> sessions/<codename>/reviews/workspace/wf-...`
4. REVISE → fix and repeat; APPROVE → `plan_user_review`

## 4. Gate 2 — Action plan

| Phase | You do | Agent does |
|-------|--------|------------|
| `plan_user_review` | **`accept plan`** (or add `plan-feedback.md`) | `./scripts/workflow-accept-plan.sh <codename>` |

Syncs tasks → `session.json`, creates worktrees, `phase: implementation`.

Reopen: `python3 scripts/workflow-reopen-plan.py <codename>`

## 5. Implementation

Parent agent edits `sessions/<codename>/worktrees/**` (or hub paths when `mode: hub`). Marks tasks done in `session.json`.

## 6. Autonomous code review loop

```bash
python3 scripts/workflow-begin-code-review.py <codename>
```

Each iteration: code-reviewer skill (changeset) → enrich scope → synthesizer → `workflow-code-review-advance.py`. INCOMPLETE/FAIL → agent fixes and re-runs. PASS → `delivery`.

## 7. Gate 3 — Delivery report

```bash
python3 scripts/workflow-write-delivery-report.py <codename>
```

Agent presents `artifacts/delivery-report.md`; `phase: completed`.

## Resume after interruption

New message **`/workflow`** in the same bound chat:

- Read `workflow.json` `phase` and context **Resume** line
- Continue from that phase — do not restart from chat history

Example mid-plan: phase `plan_loop`, iteration 2, last `REVISE` → resume plan-author/reviewer loop.

## Status

**`/workflow status`** — one-screen summary from `workflow.json` and artifact paths.

## Scripts reference

| Script | When |
|--------|------|
| `workflow-plan-synthesize.py` | After plan reviewer Task |
| `workflow-accept-plan.sh` | User accept plan |
| `workflow-begin-code-review.py` | All tasks done |
| `workflow-code-review-enrich-scope.py` | After code-reviewer scope collector |
| `workflow-code-review-advance.py` | After code-reviewer synthesizer |
| `workflow-write-delivery-report.py` | Code review PASS |
| `workflow-reopen-brief.py` / `workflow-reopen-plan.py` | Unfreeze gates |

Full skill: `.cursor/skills/workflow-orchestrator/SKILL.md`
