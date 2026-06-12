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

## Related

- Session bind (unchanged): `/start-work` → [session-orchestrator](../.cursor/skills/session-orchestrator/SKILL.md)
- Cross-session inbox: [SESSIONS.md](../SESSIONS.md)
- Retirement checklist: `sessions/_template/artifacts/session-orchestrator-retirement-checklist.md`
