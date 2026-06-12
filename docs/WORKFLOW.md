# Workflow orchestrator walkthrough

Single-session pipeline: **Problem → Plan → Code → Review → PR → CI → Delivery**. One Cursor chat, **two user gates** (brief and plan). Correlated **inbox feedback** from the registered program parent counts at gates (via `program-route-feedback.py`); poll every 2 minutes while awaiting a gate.

## Prerequisites

- Hub bound to a session codename (`./scripts/resolve-session.sh`)
- Optional product repos in `repos.yaml` for worktree implementation

## 1. Start

```bash
./scripts/resolve-session.sh          # must print codename
```

In chat: **`/workflow-orchestrator`**

Conductor bootstraps `workflow.json` + `artifacts/` from `sessions/_template/` if missing.

## 2. Gate 1 — Problem brief

| Phase | You do | Agent does |
|-------|--------|------------|
| `intake` | Answer analyst questions | Draft `artifacts/problem-brief.md` |
| `brief_review` | **`accept brief`** (or correlated inbox) | Sets `gates.brief_accepted`; enters plan loop |

Reopen: `python3 scripts/workflow-reopen-brief.py <codename>`

**Inbox at gate:** Program parents route gate commands with:

```bash
python3 scripts/program-route-feedback.py <parent> <child> \
  --gate brief_review --message "accept brief"
```

Use `--gate plan_user_review --message "accept plan"` (or `reopen brief` / `reopen plan`) at the plan gate. Raw `session-inbox.sh write` gate commands are rejected unless they include the program-route marker. While in `brief_review`, poll every 2 minutes:

```bash
python3 scripts/workflow-pull-inbox-gate.py <codename> --apply
```

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
| `plan_user_review` | **`accept plan`** (or correlated inbox; or add `plan-feedback.md`) | `./scripts/workflow-accept-plan.sh <codename>` |

Syncs tasks → `session.json`, creates worktrees, `phase: implementation`.

Reopen: `python3 scripts/workflow-reopen-plan.py <codename>`

**Inbox at gate:** e.g. `accept plan`, `reopen plan`, or plan revision notes — same 2-minute pull as brief gate.

## 5. Implementation → code review (automatic)

Parent agent edits `sessions/<codename>/worktrees/**`. When a task slice is complete, the conductor **immediately** runs:

```bash
python3 scripts/workflow-mark-implementation-ready.py <codename> <task-id>
```

No commit gate. Uncommitted worktree changes are included in review scope.

## 6. Autonomous code review loop

Each iteration: code-reviewer skill (changeset + working tree) → `python3 scripts/workflow-code-review-enrich-scope.py <codename> sessions/<codename>/reviews/workspace/<review-id>` → Task specialists → synthesizer → `python3 scripts/workflow-code-review-advance.py <codename>`.

**INCOMPLETE** → parent fixer ([code-fixer.md](../.cursor/skills/workflow-orchestrator/rules/code-fixer.md)): fix REQUIRED; accept/refuse SUGGESTION/NIT in `artifacts/code-review-disposition.md`; re-run until **PASS**.

## 7. PR creation (automatic)

After code review **PASS**, the conductor commits (`.cursor/skills/git-commit/SKILL.md`) and opens a draft PR (`.cursor/skills/pr-create/SKILL.md`) against `pr_target_branch` from `repos.yaml`. Records PR URL on the active task.

```bash
python3 scripts/workflow-advance-pr-creation.py <codename> SUCCESS <pr_url>
```

## 8. CI observe loop (automatic)

After PR creation SUCCESS, the conductor polls CI and auto-fixes:

- **GREEN** → delivery
- **CONFLICT** → rebase onto target branch, force-push, re-poll
- **TEST_FAILURE** → parent runs `ci-fixer.md`, commits fix, force-pushes, re-polls
- 5-iteration cap; escalates with CI log summary after max

```bash
python3 scripts/workflow-ci-observe-advance.py <codename> <verdict>
```

## 9. Delivery report (inform only)

After CI observe **GREEN**, the agent auto-runs:

```bash
python3 scripts/workflow-write-delivery-report.py <codename>
```

Presents `artifacts/delivery-report.md`; `phase: completed`. Not a user gate.

## Resume after interruption

New message **`/workflow-orchestrator`** in the same bound chat:

- Read `workflow.json` `phase` and context **Resume** line
- Continue from that phase — do not restart from chat history

Example mid-plan: phase `plan_loop`, iteration 2, last `REVISE` → resume plan-author/reviewer loop.

## Status

**`/workflow-orchestrator status`** — one-screen summary from `workflow.json` and artifact paths.

## RC release smoke

Before tagging **1.0.0-rc.1**, run [RC-SMOKE-CHECKLIST.md](RC-SMOKE-CHECKLIST.md) once on the merged rc tip and record pass/fail in the delivery report.

## Scripts reference

| Script | When |
|--------|------|
| `workflow-plan-synthesize.py` | After plan reviewer Task |
| `workflow-accept-plan.sh` | User accept plan |
| `workflow-accept-brief.sh` | User accept brief |
| `workflow-pull-inbox-gate.py` | Poll inbox at gates (every 2m); `--apply` when correlated |
| `workflow-mark-implementation-ready.py` | Per-task slice complete |
| `workflow-code-review-enrich-scope.py` | After code-reviewer scope collector |
| `workflow-code-review-advance.py` | After code-reviewer synthesizer |
| `workflow-advance-pr-creation.py` | After commit + draft PR |
| `workflow-ci-observe-advance.py` | After CI poll / fix attempt |
| `workflow-write-delivery-report.py` | CI observe GREEN |
| `workflow-reopen-brief.py` / `workflow-reopen-plan.py` | Unfreeze gates |
| `workflow-begin-code-review.py` | Legacy — all tasks done (prefer mark-implementation-ready) |

Full skill: `.cursor/skills/workflow-orchestrator/SKILL.md`
