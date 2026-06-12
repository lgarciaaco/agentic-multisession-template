---
name: sessions-orchestrator
description: >-
  Program-level orchestrator: ingest work, decompose into child sessions running
  /workflow-orchestrator, monitor gates, route inbox feedback, per-child PR review.
---

# Sessions orchestrator

Multi-session program conductor. Parent chat coordinates; each child runs **`/workflow-orchestrator`** in its own chat.

## Target

1. `./scripts/resolve-session.sh` → bound **parent** session
2. State: `sessions/<parent>/program.json`
3. Artifacts: `artifacts/program-plan.md`, `artifacts/program-status.md`, optional `artifacts/program-ingest.md`

## Triggers

| Trigger | Action |
|---------|--------|
| `/sessions-orchestrator` | Start or resume program pipeline |
| `/sessions-orchestrator status` | One-screen status from `program.json` + monitor |

## Start

1. Resolve parent codename; ensure `program.json` exists (copy from `sessions/_template/program.json` if missing).
2. Accept ingest (chat text, file path, or `artifacts/program-ingest.md`).
3. Run `python3 scripts/program-decompose.py <parent> [ingest]` → `artifacts/program-plan.md`.
4. Present proposed children; **block bootstrap** until user says **`approve decomposition`**.

## Child bootstrap (after approval)

After the user says **`approve decomposition`**, run one parent-side command:

```bash
python3 scripts/program-bootstrap-children.py <parent> --approve
```

This reads `proposed_children` from `program.json`, creates each child session (`new-session.sh`, `set-session-scope.sh`), registers `active_children`, and sets `decomposition_approved: true`.

**Inside tmux:** opens one detached window per child (parent tab unchanged). Each child tab is labeled with the hub prefix + codename, binds via `@workspace-codename`, and auto-starts **`/workflow-orchestrator`** via `$(cat .hub-launcher) --reuse --workflow`.

**Outside tmux:** exits 0 and prints manual steps (new tab per child, launcher `--reuse --workflow`).

Parent never edits child worktrees. Child chats run **`/workflow-orchestrator`** autonomously in their tabs.

## Monitor

```bash
python3 scripts/program-monitor.py <parent>
./scripts/program-status-report.sh <parent>
```

Re-run on gate events and during periodic standups. Report path: `artifacts/program-status.md`.

## Parent gate UX (dynamic)

When monitor shows `pending_gate` of `brief_review` or `plan_user_review` on a child:

| Child phase | Accept | Block / reopen |
|-------------|--------|----------------|
| `brief_review` | `accept brief` | `reopen brief` |
| `plan_user_review` | `accept plan` | `reopen plan` |

Respond to **one child** while others continue, or batch — your choice.

Route feedback:

```bash
python3 scripts/program-route-feedback.py <parent> <child> \
  --gate brief_review --message "accept brief"
python3 scripts/program-route-feedback.py <parent> <child> \
  --gate plan_user_review --message "reopen plan"
```

Child inbox + inbox gate correlation applies in the child chat.

## Child completion → PR review

When a child reaches workflow phase `completed`:

1. `python3 scripts/program-merge-order.py <parent>` (when multiple active PRs)
2. Load **code-reviewer** skill (`/pr-review`) scoped to that child's PR and worktree
3. One review per child; sub-agents OK

## Writable

Parent: `sessions/<parent>/program.json`, `artifacts/program-*`, hub scripts/skills/docs in worktree per plan.

## References

- [docs/PROGRAM_ORCHESTRATOR.md](../../../docs/PROGRAM_ORCHESTRATOR.md)
- Child pipeline: [workflow-orchestrator](../workflow-orchestrator/SKILL.md)
- Session bind: [session-orchestrator](../session-orchestrator/SKILL.md) (`/start-work`)
