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

When session B runs `/workflow-orchestrator` and is waiting at a user gate, correlated inbox messages count as user feedback. Other sessions (monitoring agents) can approve or revise without switching chats.

**Authorization:** Inbox gate auto-apply for gate commands (`accept brief`, `accept plan`, `reopen brief`, `reopen plan`) is **disabled** — use chat gate commands, `./scripts/workflow-accept-*.sh`, or (for program children) **`program-route-feedback.py`** (tmux send-keys). Self-writes and sibling gate commands are rejected if present in inbox. **`session-inbox.sh write`** requires the bound caller to match `from` (or authenticated `--as <codename>` when bound). Chat gate commands and `./scripts/workflow-accept-*.sh` remain authorized user paths. **Program parent→child** gate commands and corrections use tmux send-keys — not inbox files. Bound and unbound sessions cannot edit `sessions/_inbox/` directly — use the inbox write CLI.

| Target phase | First line of message | Effect |
|--------------|----------------------|--------|
| `brief_review` | `accept brief` or `accept` | Accept brief → plan loop |
| `brief_review` | `reopen brief` | Reopen brief |
| `brief_review` | anything else | Brief correction for conductor |
| `plan_user_review` | `accept plan` | Accept plan → implementation |
| `plan_user_review` | `reopen plan` | Reopen plan |
| `plan_user_review` | anything else | Plan feedback → `plan-feedback.md`, re-enter plan loop |

Optional prefix: `workflow: accept plan`

The workflow conductor polls every **2 minutes** while at a gate:

```bash
python3 scripts/workflow-pull-inbox-gate.py <to-codename> --apply
```

Processed inbox blocks are tracked in `workflow.json` → `gates.inbox.processed_markers`.

## Program orchestrator routing

| Sender | Tool | Message type |
|--------|------|--------------|
| Parent → child gate accept/reopen | `python3 scripts/program-route-feedback.py` | `--gate` + exact `--message`; sends to child tmux pane via send-keys |
| Parent → child review note | `python3 scripts/program-route-feedback.py` (omit `--gate`) | Free-text correction sent to child pane as chat input |
| Child → parent blocker | `./scripts/session-inbox.sh write <child> <parent> "…"` | Escalation at user gates; also persisted in child gate artifact **Open questions** |

Prose approval (e.g. "brief looks good — proceed") is **not** `accept brief`. Parents must use `program-route-feedback.py` with the exact command to cross a gate.
