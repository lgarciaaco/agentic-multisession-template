---
name: hub-upgrade
description: Check template version vs upstream and upgrade hub scripts/hooks/docs in place. Use when user asks about template version, hub upgrade, or "is there a new version".
---

# Hub upgrade (in place)

**Goal:** Refresh the shared hub layer (scripts, hooks, docs) without wiping `repos/`, `repos.yaml`, or `sessions/<codename>/`.

Triggers: `template version`, `hub upgrade`, `upgrade hub`, `is there a new template version`, `upgrade`

---

## 1. Check only (user asks — do not upgrade yet)

```bash
./scripts/hub-status.sh
```

Read JSON fields:

| Field | Use |
|-------|-----|
| `current_version` / `latest_version` | What they're on vs upstream |
| `update_available` | Whether an upgrade exists |
| `plain_summary` | Plain-language hub changes between versions |
| `pending_releases[]` | Per-release hub + session detail |
| `session_guidance.impact` | `none` / `optional` / `required` |
| `session_guidance.notes` | Steps for existing sessions when impact is not `none` |

**Tell the user:**

1. **Hub changes** — summarize `plain_summary` and key bullets (not raw changelog dump).
2. **Session notes** — if `impact: none`, say existing sessions need nothing. If `optional` or `required`, list `session_guidance.notes` and which releases drove them.

Stop and wait for explicit **upgrade** / **go ahead** before step 2.

---

## 2. Upgrade (user says upgrade)

Preview first when unsure:

```bash
./scripts/hub-upgrade.sh --dry-run --yes
./scripts/hub-upgrade.sh --yes
./scripts/hub-upgrade.sh --yes --to 0.4.0
```

Use `--allow-untrusted-upstream` only when `.hub-upstream` points at a non-default template URL.

Then run `post_upgrade_steps` from the JSON (pip, `install-workspace-agent.sh`, both smoke test suites).

**Does not touch:** `repos/`, `repos.yaml`, `sessions/<codename>/` (except committed template examples under `sessions/_template/` etc.).

**Optional upstream override:** copy `.hub-upstream.example` → `.hub-upstream`, set `WORKSPACE_TEMPLATE_UPSTREAM`, or `WORKSPACE_TEMPLATE_REF` (default `main`). Non-default URLs require `--allow-untrusted-upstream`.

---

## 3. After upgrade — session catch-up

Only when release `session_impact` was `optional` or `required`:

| Situation | Action |
|-----------|--------|
| Worktrees (0.3.0+) | Ensure tasks have `"repo"`; `./scripts/ensure-worktrees.sh <codename>` |
| Inbox (0.2.0+) | No folder edits; mention `./scripts/session-inbox.sh` if coordinating across chats |
| Stale `BOUNDARIES.md` | Compare with `sessions/_template/BOUNDARIES.md`; patch active sessions if user wants |

Do **not** bulk-edit session folders unless the user agrees or impact was `required`.

---

## Rules

- Never re-bootstrap from scratch unless user explicitly asks.
- Never delete `repos/` or session history as part of upgrade.
- **Only** `./scripts/hub-upgrade.sh` may refresh hub-root `scripts/`, hooks, and docs — agents do not hand-edit those paths. Product work stays in worktrees.
