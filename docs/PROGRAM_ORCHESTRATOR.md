# Program orchestrator

Multi-session coordination layer above single-session [`/workflow-orchestrator`](../.cursor/skills/workflow-orchestrator/SKILL.md).

## Architecture

```text
/sessions-orchestrator (parent chat)
  ingest → decompose → [approve decomposition]
  → bootstrap child sessions
  → monitor gates → route tmux feedback to child panes
  → per-child /pr-review on completion

/workflow-orchestrator (each child chat)
  Problem → Plan → Code → Review → PR → CI → Delivery
```

## Artifacts (parent session)

| Path | Purpose |
|------|---------|
| `program.json` | Active children, gate queue, merge hints |
| `artifacts/program-ingest.md` | Raw ingest (optional) |
| `artifacts/program-plan.md` | Decomposed child plan |
| `artifacts/program-status.md` | Monitor report |

Template: `sessions/_template/program.json`

## Scripts

| Script | Role |
|--------|------|
| `scripts/program-decompose.py` | Ingest → proposed children |
| `scripts/program-bootstrap-children.py` | Bootstrap children + open tmux tabs |
| `scripts/program-monitor.py` | Read child workflow phases/gates |
| `scripts/program-status-report.sh` | Write `artifacts/program-status.md` |
| `scripts/program-route-feedback.py` | Parent → child tmux pane at gates (send-keys) |
| `scripts/program-merge-order.py` | PR merge sequencing |
| `scripts/lib/program_state.py` | Load/save/validate `program.json` |

## Success criteria mapping

| SC | Delivered by |
|----|----------------|
| SC-1 | `/sessions-orchestrator` skill + decompose + approval gate |
| SC-2 | monitor + status report |
| SC-3 | route-feedback + parent gate UX in skill |
| SC-4 | merge-order + `/pr-review` section |
| SC-5 | this doc + tests + AGENTS.md |

## Program child tmux tabs

After **approve decomposition**, the parent runs:

```bash
python3 scripts/program-bootstrap-children.py <parent> --approve
```

When `TMUX` is set, the script opens one detached window per child in the same tmux session. Each window:

- Renames to `{hub-prefix}{codename}` (same as single-session bind)
- Sets pane option `@workspace-codename` before the agent starts
- Runs `$(cat .hub-launcher) --reuse --workflow` so the child auto-starts `/workflow-orchestrator` without the session picker

The parent window stays selected. Bootstrap persists each child's `pane_id` on `program.json` → `active_children[]` for later routing.

### Shared pane helpers (`program_child_tabs.py`)

Program routing and future tab cleanup (pc3) share:

- `resolve_child_pane(root, codename, stored_pane_id=None)` — live pane id from stored value or `@workspace-codename` scan
- `send_to_child_pane(pane_id, text)` — `tmux send-keys` with trailing Enter
- `persist_child_panes(program, windows)` — merge bootstrap window records into `program.json`

Outside tmux, route scripts fail fast with manual steps (no inbox fallback).

## Check children / status (one screen)

When the user checks children or runs `/sessions-orchestrator status`:

1. `python3 scripts/program-monitor.py <parent>` + `./scripts/program-status-report.sh <parent> [--reviews-json path]`
2. Spawn **Task(child-reviewer)** per active child in parallel — model `claude-4.6-sonnet-medium-thinking` per [agents/child-reviewer.md](../.cursor/skills/sessions-orchestrator/agents/child-reviewer.md)
3. Merge subagent returns into status report via `--reviews-json` (see child-reviewer **Parent synthesis**)
4. Parent chat: **one screen max** — `Parent next` plus slim table only

```text
Parent next: <from parent_next_action>

| Child | Phase | Gate | Next |
|-------|-------|------|------|
| child-1 | plan_user_review | plan | Accept plan or send corrections |
| child-2 | implementation | — | Continue t3 in worktree |
```

**Gate column:** `brief` | `plan` | `—`. **Next** column: one line from subagent **Next** section.

**Not in chat:** **Your action — codename** blocks, long Status prose, or full **Parent assessment** / **Cross-child check** — those live in `artifacts/program-status.md` only.

Monitor JSON `gate_review.sibling_program_context` supplies read-only sibling decomposition goals (and plan summaries at plan gates) so child-reviewer Tasks catch cross-child overlap without reading sibling session folders.

## Merge boundaries (xray program)

Self-hosted hub **`template`** worktree per child. pc6 (child-6) documents ownership to reduce PR conflict with parallel siblings.

| Area | pc6 (child-6) owns | pc2 (child-2) owns | pc3 (child-3) owns |
|------|-------------------|-------------------|-------------------|
| `scripts/lib/program_monitor.py` | Sibling context helpers; `child_gate_review` / `child_snapshot` enrichment | — | EOF `monitor_program` cleanup hook only |
| `scripts/program-monitor.py` | Slim `format_text` table + sibling lines | — | — |
| `scripts/program-status-report.sh` | Detail sections + `--reviews-json` merge | — | — |
| `.cursor/skills/sessions-orchestrator/` | child-reviewer.md, Check children slim format, model slug | Parent gate routing → tmux send-keys | Tab cleanup on child `completed` |
| `docs/PROGRAM_ORCHESTRATOR.md` | This section + cross-child review | Inbox routing section | Tab cleanup section |

**Recommended rebase order:** pc6 monitor helpers first (isolated block), then pc3 append cleanup hook, then pc2 routing skill edits in non-overlapping sections.

**pc6 defers:** `program-route-feedback.py`, inbox program paths, `program_child_tabs.py` send-keys routing (pc2); tmux window kill on completion (pc3).

## Parent gate review (mandatory)

Parent sessions coordinate; they do not edit child sessions.

| Feedback type | Tool | Example |
|---------------|------|---------|
| Accept / reopen gate | `python3 scripts/program-route-feedback.py` | Sends exact gate command to child tmux pane via send-keys |
| Brief or plan correction | `python3 scripts/program-route-feedback.py` (no `--gate`) or `--correction` | Free-text sent to child pane as chat input |

**Read-only review (mandatory at gates):** inspect child gate artifacts via monitor `gate_review`; compare to decomposition scope and `sibling_program_context`; read full assessments in `artifacts/program-status.md` before routing. Never patch child artifacts or worktrees from the parent chat. Monitor JSON includes `gate_review` paths, `sibling_program_context`, and `parent_next_action`.

**Gate commands must be exact.** Prose such as "brief looks good — proceed" classifies as `brief_correction`, not `accept brief`. Use full CLI invocations when approving a gate:

```bash
python3 scripts/program-route-feedback.py <parent> <child> \
  --gate brief_review --message "accept brief"
python3 scripts/program-route-feedback.py <parent> <child> \
  --gate plan_user_review --message "accept plan"
python3 scripts/program-route-feedback.py <parent> <child> \
  --gate brief_review --message "reopen brief"
python3 scripts/program-route-feedback.py <parent> <child> \
  --gate plan_user_review --message "reopen plan"
python3 scripts/program-route-feedback.py <parent> <child> \
  --message "Tighten SC-2 wording — checklist count should be 13."
```

Gate and correction messages arrive in the **child chat** as typed prompts (not inbox files). Child workflow handles `accept brief` / `accept plan` in chat; corrections update the gate artifact in the child session.

## Related

- Single-session bind (unchanged): `/start-work` → [session-start](../.cursor/skills/session-start/SKILL.md)
- Cross-session inbox: [SESSIONS.md](../SESSIONS.md)
- Retirement checklist: `sessions/_template/artifacts/session-orchestrator-retirement-checklist.md`
