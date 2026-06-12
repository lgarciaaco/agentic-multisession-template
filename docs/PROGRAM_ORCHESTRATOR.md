# Program orchestrator

Multi-session coordination layer above single-session [`/workflow-orchestrator`](../.cursor/skills/workflow-orchestrator/SKILL.md).

## Architecture

```text
/sessions-orchestrator (parent chat)
  ingest → decompose → [approve decomposition]
  → bootstrap child sessions
  → monitor gates → route inbox feedback
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
| `scripts/program-route-feedback.py` | Parent → child inbox at gates |
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

The parent window stays selected. Outside tmux, the script prints manual bind/launcher steps and exits 0.

See [SESSIONS.md](../SESSIONS.md) § Program orchestrator child tabs.

## `/sessions-orchestrator status` (one screen)

Read `program.json` and monitor report; print:

```markdown
## Program status — <parent>

- **Decomposition approved:** <bool>
- **Parent next:** <mandatory action from monitor>
- **Children:** table (phase, pending_gate, gate_review artifact paths)
- **Gate review:** per pending child — artifact path, decomposition scope, assessment prompt
- **Next command:** run monitor + status report when any pending_gate; otherwise monitor on interval
```

Do not ask the user to relay messages between agents or sessions. Do not say "accept X when you've reviewed" — **review first, always**.

## Parent gate review (mandatory)

Parent sessions coordinate; they do not edit child sessions.

| Feedback type | Tool | Example |
|---------------|------|---------|
| Accept / reopen gate | `python3 scripts/program-route-feedback.py` | `python3 scripts/program-route-feedback.py <parent> <child> --gate brief_review --message "accept brief"` (also `--gate plan_user_review --message "accept plan"`; reopen with `--message "reopen brief"` / `"reopen plan"`) |
| Brief or plan correction | `session-inbox.sh write <parent> <child> "…"` | Prose review notes |

**Read-only review (mandatory at gates):** inspect child `artifacts/problem-brief.md` or `artifacts/action-plan.md`; compare to decomposition scope; present assessment before routing. Never patch child artifacts or worktrees from the parent chat. Monitor JSON includes `gate_review` paths and `parent_next_action`.

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
```

**Child → parent escalation:** program children dual-write open questions and blockers to the parent inbox and persist them in the gate artifact before presenting a user gate (see workflow conductor rules).

## Related

- Session bind (unchanged): `/start-work` → [session-orchestrator](../.cursor/skills/session-orchestrator/SKILL.md)
- Cross-session inbox: [SESSIONS.md](../SESSIONS.md)
- Retirement checklist: `sessions/_template/artifacts/session-orchestrator-retirement-checklist.md`
