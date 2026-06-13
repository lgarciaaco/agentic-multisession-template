# Session inbox

One file per target session: `<codename>.md` (e.g. `alpha.md`).

**Write (session A → session B):** `./scripts/session-inbox.sh write <from> <to> "message"`

```bash
./scripts/session-inbox.sh write bravo alpha "Feature shipped — ready for review."
```

Message lands in `sessions/_inbox/alpha.md` (target = `<to>`).

**Read:** bind session B (injected into chat context) or:

```bash
./scripts/session-inbox.sh read alpha
```

Any bound session may send messages here via `./scripts/session-inbox.sh write <from> <to> "…"` — direct path edits under `sessions/_inbox/` are blocked when bound. Do not put secrets in inbox files.

## Workflow gate feedback

When session B runs `/workflow-orchestrator` and is waiting at a user gate, the conductor polls inbox and **classifies** correlated messages. Inbox `--apply` does **not** auto-mutate workflow state for gate commands or unauthorized feedback (post-rc.4). Use chat gate commands, `./scripts/workflow-accept-*.sh`, or (for program children) **`program-route-feedback.py`** (tmux send-keys) to cross gates.

**Authorization:** Inbox gate auto-apply for gate commands (`accept brief`, `accept plan`, `reopen brief`, `reopen plan`) is **disabled** — `gate_command_sender_authorized` always returns false. Self-writes, sibling gate commands, and parent ordinary inbox writes are rejected at apply time and **not** marked processed (they remain in `pending` for audit). **`session-inbox.sh write`** requires the bound caller to match `from`; unbound writes require explicit `--as <codename>` matching `from`. Chat gate commands and `./scripts/workflow-accept-*.sh` remain authorized user paths. **Program parent→child** gate commands and corrections use tmux send-keys — not inbox files. Bound and unbound sessions cannot edit `sessions/_inbox/` directly — use the inbox write CLI.

**Standalone `brief_correction` / `plan_feedback`:** No inbox auto-apply path is enabled (`feedback_sender_authorized` returns false for program children and standalone sessions today). Classified feedback is rejected at apply; use chat or tmux routing instead.

| Target phase | First line of message | Classification (inbox apply does not mutate) |
|--------------|----------------------|---------------------------------------------|
| `brief_review` | `accept brief` or `accept` | Gate command: accept brief |
| `brief_review` | `reopen brief` | Gate command: reopen brief |
| `brief_review` | anything else | Brief correction text for conductor |
| `plan_user_review` | `accept plan` | Gate command: accept plan |
| `plan_user_review` | `reopen plan` | Gate command: reopen plan |
| `plan_user_review` | anything else | Plan feedback text for conductor |

Optional prefix: `workflow: accept plan`

The workflow conductor polls every **2 minutes** while at a gate:

```bash
python3 scripts/workflow-pull-inbox-gate.py <to-codename> --apply
```

Only **successfully applied** inbox blocks are tracked in `workflow.json` → `gates.inbox.processed_markers`. Rejected blocks stay pending.

## Program orchestrator routing

| Sender | Tool | Message type |
|--------|------|--------------|
| Parent → child gate accept/reopen | `python3 scripts/program-route-feedback.py` | `--gate` + exact `--message`; sends to child tmux pane via send-keys |
| Parent → child review note | `python3 scripts/program-route-feedback.py` (omit `--gate`) | Free-text correction sent to child pane as chat input |
| Child → parent blocker | `./scripts/session-inbox.sh write <child> <parent> "…"` | Escalation at user gates; also persisted in child gate artifact **Open questions** |

Prose approval (e.g. "brief looks good — proceed") is **not** `accept brief`. Parents must use `program-route-feedback.py` with the exact command to cross a gate.
