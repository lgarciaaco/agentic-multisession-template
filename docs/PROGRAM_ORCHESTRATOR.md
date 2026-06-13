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

Program routing and completed-child tab cleanup share:

- `resolve_child_pane(root, codename, stored_pane_id=None)` — live pane id from stored value (hub cwd validated) or `@workspace-codename` scan
- `resolve_child_window(root, codename, pane_id=..., window_label=...)` — resolve pane for routing or cleanup
- `send_to_child_pane(pane_id, text)` — `tmux send-keys` with trailing Enter
- `persist_child_panes(program, windows)` — merge bootstrap window records into `program.json`
- `close_child_window(pane_id)` — kill the tmux window containing the pane (used by tab cleanup)

Outside tmux, route scripts fail fast with manual steps (no inbox fallback).

### Completed-child tab cleanup

On each `program-monitor.py` pass, `monitor_program` calls `cleanup_completed_children` before building child snapshots:

1. For each entry in `program.json` → `active_children[]`, read the child's `workflow.json` phase.
2. When phase is **`completed`**, set `active_children[].status` to `completed` and persist `program.json` when any status changes.
3. When running inside tmux, resolve the child window from stored `pane_id` / `window_label` (or live `@workspace-codename` scan) via `resolve_child_window`.
4. Call `close_child_window` only when `is_safe_child_close_target` passes:
   - child codename must differ from the parent codename
   - pane must be live and match the child codename under hub root (`_pane_matches_child`)
   - target window must not be the parent's current tmux window

Cleanup is best-effort: a failed close leaves the window open; the next monitor pass retries while phase stays `completed`.

### Local-trust boundaries

Program parent routing uses **local-trust** delivery paths on the machine where tmux runs:

- **`program-route-feedback.py`** validates the caller is bound to the parent session (`resolve_codename`) and that the child's `workflow.json` phase matches the requested `--gate` before `send-keys`. It skips when an **accept** gate command targets an already-accepted gate, when an identical message was sent within the 5-minute cooldown, or (for free-text corrections) when the child is not at `brief_review` / `plan_user_review`. CLI prints `skipped: <reason>` or `sent: <message>`. `--force` overrides already-accepted and dedupe skips for gate routes; wrong-phase gate routes still fail. For corrections (no `--gate`), `--force` also overrides the phase guard. It does **not** cryptographically authenticate the target pane — trust is local to the tmux server and hub filesystem layout.
- **`resolve_child_pane`** reuses a stored `pane_id` only when `_pane_matches_child` passes (live pane, matching `@workspace-codename`, cwd under hub root). Otherwise it scans hub panes or fails clearly.
- **`route_correction`** (free-text) requires the caller bound to the parent session; skips outside gate phases unless `--force`. Corrections are chat input, not gate commands — do not use them as progress nudges during inner-loop phases.
- **`program-monitor.py`** exposes per-child `routable`, `route_skip_reason`, `last_routed_at`, and `last_routed_message` so autonomous monitor loops can avoid duplicate sends.
- **`workflow-accept-brief.sh`** and **`workflow-accept-plan.sh`** are local-trust CLIs: they take an explicit `<codename>` argument (no `resolve_codename` caller check). Run only from the child chat or a trusted shell on the hub machine.

Standalone workflow sessions may still poll inbox at gates; program children rely on tmux routing above.

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

## Parent gate review (mandatory)

Parent sessions coordinate; they do not edit child sessions.

| Feedback type | Tool | Example |
|---------------|------|---------|
| Accept / reopen gate | `python3 scripts/program-route-feedback.py` | Sends exact gate command to child tmux pane via send-keys |
| Brief or plan correction | `python3 scripts/program-route-feedback.py` (no `--gate`) or `--correction` | Free-text sent to child pane as chat input |

**Read-only review (mandatory at gates):** inspect child gate artifacts via monitor `gate_review`; compare to decomposition scope and `sibling_program_context`; read full assessments in `artifacts/program-status.md` before routing. Never patch child artifacts or worktrees from the parent chat. Monitor JSON includes `gate_review` paths, `sibling_program_context`, and `parent_next_action`. Route each gate command **once per gate** — check `routable` and `route_skip_reason` before re-sending; do not use free-text corrections during inner-loop phases (see [Local-trust boundaries](#local-trust-boundaries)).

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
