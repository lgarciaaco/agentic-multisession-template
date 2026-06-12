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

**Authorization:** Inbox auto-apply for gate commands (`accept brief`, `accept plan`, `reopen brief`, `reopen plan`) accepts only from the target session's registered program parent when the message includes the `[program-orchestrator gate=…]` marker from `program-route-feedback.py` **and** verified write provenance (sidecar under `sessions/_inbox/.provenance/` — trust-on-write via the program-route API, not HMAC-signed; cryptographic signing is out of scope pending write-path hardening in sibling work). Self-writes and sibling gate commands are rejected, marked processed, and do not advance workflow. Inbox `From` headers are not cryptographically bound — use `program-route-feedback.py` for cross-session gate auto-apply. **`session-inbox.sh write`** requires the bound caller to match `from` (or authenticated `--as <codename>`); sibling impersonation of parent is rejected at write time. Chat gate commands and `./scripts/workflow-accept-*.sh` remain authorized user paths. **Brief corrections and plan feedback** auto-apply only from the registered program parent (`feedback_sender_authorized` in `workflow_inbox_gate.py`); siblings, self-writes, and standalone sessions (no program parent) are rejected with `unauthorized_feedback_sender`, marked processed, and do not mutate brief or plan-feedback artifacts. Bound sessions cannot edit `sessions/_inbox/` directly — use the inbox write CLI.

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
| Parent → child gate accept/reopen | `python3 scripts/program-route-feedback.py` | Required `--gate` (`brief_review` or `plan_user_review`) and `--message` (e.g. `"accept brief"`, `"accept plan"`, `"reopen brief"`, `"reopen plan"`). Routed inbox body uses the gate string on the first line for child `workflow-pull-inbox-gate.py` correlation. |
| Parent → child review note | `./scripts/session-inbox.sh write <parent> <child> "…"` | Free-text → `brief_correction` or `plan_feedback` |
| Child → parent blocker | `./scripts/session-inbox.sh write <child> <parent> "…"` | Escalation at user gates; also persisted in child gate artifact **Open questions** |

Prose approval (e.g. "brief looks good — proceed") is **not** `accept brief`. Parents must use `program-route-feedback.py` with the exact command to cross a gate.
