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

Any bound session may write here (`sessions/_inbox/` is shared). Do not put secrets in inbox files.

## Workflow gate feedback

When session B runs `/workflow-orchestrator` and is waiting at a user gate, correlated inbox messages count as user feedback. Other sessions (monitoring agents) can approve or revise without switching chats.

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
| Parent → child gate accept/reopen | `python3 scripts/program-route-feedback.py` | Exact gate command on first line (`accept brief`, `accept plan`, `reopen brief`, `reopen plan`) |
| Parent → child review note | `./scripts/session-inbox.sh write <parent> <child> "…"` | Free-text → `brief_correction` or `plan_feedback` |
| Child → parent blocker | `./scripts/session-inbox.sh write <child> <parent> "…"` | Escalation at user gates; also persisted in child gate artifact **Open questions** |

Prose approval (e.g. "brief looks good — proceed") is **not** `accept brief`. Parents must use `program-route-feedback.py` with the exact command to cross a gate.
