# Workflow orchestrator walkthrough

Single-session pipeline: **Problem → Plan → Code → Review**. One Cursor chat, **two user gates** (brief and plan).

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

1. Task(plan-author) → `artifacts/action-plan.md` (dispositions SUGGESTION/NIT on REVISE)
2. Task(plan-reviewer) → `findings/plan.json` (validates dispositions on later passes)
3. `python3 scripts/workflow-plan-synthesize.py <codename> sessions/<codename>/reviews/workspace/wf-...`
4. REVISE → author/reviewer repeat until APPROVE (open SUGGESTION/NIT cleared; refusals validated) → `plan_user_review`

Task subagent isolation is mandatory — see [conductor.md Subagent isolation](../.cursor/skills/workflow-orchestrator/rules/conductor.md).

## 4. Gate 2 — Action plan

| Phase | You do | Agent does |
|-------|--------|------------|
| `plan_user_review` | **`accept plan`** (or add `plan-feedback.md`) | `./scripts/workflow-accept-plan.sh <codename>` |

Syncs tasks → `session.json`, creates worktrees, `phase: implementation`.

Reopen: `python3 scripts/workflow-reopen-plan.py <codename>`

## 5. Implementation → code review (automatic)

Parent agent edits `sessions/<codename>/worktrees/**`. When a task slice is complete, the conductor **immediately** runs:

```bash
python3 scripts/workflow-mark-implementation-ready.py <codename> <task-id>
```

No commit gate. Uncommitted worktree changes are included in review scope.

## 6. Autonomous code review loop

Each iteration: code-reviewer skill (changeset + working tree) → `python3 scripts/workflow-code-review-enrich-scope.py <codename> sessions/<codename>/reviews/workspace/<review-id>` → Task specialists → synthesizer → `python3 scripts/workflow-code-review-advance.py <codename>`.

**INCOMPLETE** → parent fixer ([code-fixer.md](../.cursor/skills/workflow-orchestrator/rules/code-fixer.md)): fix REQUIRED; accept/refuse SUGGESTION/NIT in `artifacts/code-review-disposition.md`; re-run until **PASS**.

## 7. Delivery report (inform only)

After **PASS**, the agent auto-runs:

```bash
python3 scripts/workflow-write-delivery-report.py <codename>
```

Presents `artifacts/delivery-report.md`; `phase: completed`. Not a user gate.

## Resume after interruption

New message **`/workflow`** in the same bound chat:

- Read `workflow.json` `phase` and context **Resume** line
- Continue from that phase — do not restart from chat history

Example mid-plan: phase `plan_loop`, iteration 2, last `REVISE` → resume plan-author/reviewer loop.

## Status

**`/workflow status`** — one-screen summary from `workflow.json` and artifact paths.

## RC release smoke

Before tagging **1.0.0-rc.1**, run [RC-SMOKE-CHECKLIST.md](RC-SMOKE-CHECKLIST.md) once on the merged rc tip and record pass/fail in the delivery report.

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
