---
name: sessions-orchestrator
description: >-
  Program-level orchestrator: ingest work, decompose into child sessions running
  /workflow-orchestrator, monitor gates, route parent gate feedback via
  program-route-feedback.py (tmux send-keys), per-child PR review.
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

When any child has `pending_gate`, run monitor + status report **before** presenting status to the user.

## Check children (mandatory)

When the user asks to **check children**, **status**, **standup**, or **how are the child sessions** — or when presenting `/sessions-orchestrator status`:

1. Run `program-monitor.py` + `program-status-report.sh`.
2. Spawn **Task(child-reviewer)** per active child **in parallel** — [agents/child-reviewer.md](agents/child-reviewer.md). Pass that child's monitor JSON slice (includes `gate_review.sibling_program_context`).
3. Parent synthesizes subagent returns; **never** inline-read all child artifacts in the parent without subagents.
4. Merge Task returns into status report:

```bash
./scripts/program-status-report.sh <parent> --reviews-json /tmp/child-reviews.json
```

`child-reviews.json` keys child codenames; values hold `next`, `parent_assessment`, `cross_child_check`, `child_agent_action` from each subagent.

**Task spawn:** pass `model: claude-4.6-sonnet-medium-thinking` (must match **Model assignments** and [agents/child-reviewer.md](agents/child-reviewer.md)).

**Proactive gate review:** At `brief_review` or `plan_user_review`, each subagent **must** read the gate artifact and return **Parent assessment** + **Cross-child check**. Detail lives in `artifacts/program-status.md` — not deferred with "review when ready".

### Response format (mandatory — one screen max)

Chat output is **only** `Parent next` plus the slim table. No **Your action — codename** blocks. Full gate review detail is in `artifacts/program-status.md`.

```text
Parent next: <short imperative from parent_next_action>

| Child | Phase | Gate | Next |
|-------|-------|------|------|
| <name> | <phase> | brief | <Next line from subagent> |
| … | … | plan | … |
| … | intake | — | … |
```

**Gate column:** `brief` when `pending_gate` is `brief_review`; `plan` when `plan_user_review`; `—` otherwise.

**Next column:** one line from subagent **Next** section (or monitor `resume_hint` when no subagent ran).

Point the user to `artifacts/program-status.md` for **Parent assessment**, **Cross-child check**, and **Child agent action** per child.

Do not ask the user to relay messages between parent and child tabs.

## `/sessions-orchestrator status`

Same protocol as **Check children**: monitor + parallel Task(child-reviewer) per child (`model: claude-4.6-sonnet-medium-thinking`), merge reviews into program-status.md, then the slim chat table only.

## Parent gate review (mandatory)

At every child gate the parent **always reviews** — never defer with "accept when ready" or offer "review X / accept X" as alternatives. Gate review runs through **Check children** Task(child-reviewer) subagents; **Parent assessment** and **Cross-child check** must appear in `artifacts/program-status.md` when brief/plan artifacts exist.

1. Run monitor + status report with merged subagent reviews (or full **Check children** flow).
2. Subagent reads `gate_review.artifact_path`, `gate_review.sibling_program_context`, and compares to full `program-plan.md`.
3. Parent chat shows slim table only; user reads **Parent assessment** in program-status.md before routing.
4. User routes the gate via **`program-route-feedback.py`** (tmux send-keys) or sends free-text corrections the same way — parent does not skip the review step.

| Child phase | After review, user may say | Block / reopen |
|-------------|---------------------------|----------------|
| `brief_review` | `accept brief` | `reopen brief` |
| `plan_user_review` | `accept plan` | `reopen plan` |

Respond to **one child** while others continue, or batch — your choice.

### Parent role at gates (read-only)

The parent **reviews** child gate artifacts — it does **not** implement child work.

| Allowed | Forbidden |
|---------|-----------|
| Read child `artifacts/problem-brief.md` and `artifacts/action-plan.md` (via monitor paths or child session folder) | Edit child `artifacts/`, `workflow.json`, or worktrees |
| Route gate commands via `program-route-feedback.py` (tmux send-keys) | Offer to patch, amend, or draft child briefs/plans yourself |
| Route free-text corrections via `program-route-feedback.py` (no `--gate`) | Prose approval via inbox expecting auto-accept |

**Gate commands** (exact strings; delivered to child pane via send-keys):

```bash
python3 scripts/program-route-feedback.py <parent> <child> \
  --gate brief_review --message "accept brief"
python3 scripts/program-route-feedback.py <parent> <child> \
  --gate plan_user_review --message "reopen plan"
```

**Free-text corrections** (sent to child pane as chat input — child applies at gate):

```bash
python3 scripts/program-route-feedback.py <parent> <child> \
  --message "Tighten SC-2 wording — checklist count should be 13."
```

Requires tmux with child tabs open. Re-run `program-monitor.py` after routing.

### Idempotent routing (autonomous monitor)

Route each gate command **once per gate** — do not re-send `accept brief` / `accept plan` after the child gate clears. During inner-loop phases (`plan_loop`, `code_review_loop`, `ci_observe`, `implementation`, `pr_creation`, `delivery`), do **not** send free-text corrections (`program-route-feedback.py` without `--gate`) as progress nudges.

Before routing in an autonomous loop, read `program-monitor.py` child fields:

- `routable` — whether the route would send now
- `route_skip_reason` — why a skip would occur (already accepted, wrong phase, dedupe cooldown)
- `last_routed_at` / `last_routed_message` — last successful send per child

`program-route-feedback.py` skips duplicate routes by default (5-minute cooldown on identical normalized message). Use `--force` only when intentionally overriding a skip.

## Child completion → PR review

When a child reaches workflow phase `completed`:

1. `python3 scripts/program-merge-order.py <parent>` (when multiple active PRs)
2. Load **code-reviewer** skill (`/pr-review`) scoped to that child's PR and worktree
3. One review per child; sub-agents OK

## Writable

Parent: `sessions/<parent>/program.json`, `artifacts/program-*`, hub scripts/skills/docs in worktree per plan.

## Model assignments

| Role | Runner | Model slug | To update |
|------|--------|------------|-----------|
| Child reviewer | Task (one per child, parallel) | `claude-4.6-sonnet-medium-thinking` | [agents/child-reviewer.md](agents/child-reviewer.md) |

## References

- [docs/PROGRAM_ORCHESTRATOR.md](../../../docs/PROGRAM_ORCHESTRATOR.md)
- Child pipeline: [workflow-orchestrator](../workflow-orchestrator/SKILL.md)
- Single-session bind (not program parent): [session-start](../session-start/SKILL.md) (`/start-work`)
