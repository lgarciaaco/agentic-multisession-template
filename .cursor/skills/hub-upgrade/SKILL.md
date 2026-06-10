---
name: hub-upgrade
description: Check installed hub version vs upstream template releases and upgrade in place. Use when the user asks about template version, hub upgrade, or stable-candidate updates (1.0.0-rc.1 line).
---

# Hub upgrade

Refresh hub layer (`scripts/`, hooks, docs) without wiping `repos/`, `repos.yaml`, or `sessions/`.

Triggers: `template version`, `hub upgrade`, `upgrade hub`, `upgrade`, `stable candidate`

## 1. Check

```bash
./scripts/hub-status.sh
```

Fields: `current_version`, `latest_version`, `update_available`, `plain_summary`, `session_guidance`, `pending_releases`, `post_upgrade_steps`.

When installed version is **1.0.0-rc.1**, frame it as the **first stable candidate** — feature-complete hub template ready for real use; upstream bumps are rc tuning toward **1.0.0**, not incremental dev milestones.

Summarize hub changes + session impact (`none` / `optional` / `required`). Wait for explicit upgrade before step 2.

## 2. Upgrade

```bash
./scripts/hub-upgrade.sh --dry-run --yes   # optional preview
./scripts/hub-upgrade.sh --yes
./scripts/hub-upgrade.sh --yes --to <version>
```

`--allow-untrusted-upstream` only for non-default `.hub-upstream`.

Run `post_upgrade_steps` from status JSON (pip, `./scripts/install-workspace-agent.sh`, tests).

## 3. Session catch-up

When release impact is `optional` or `required`: worktrees + `"repo"` on tasks; refresh stale `BOUNDARIES.md` from template; mention `./scripts/session-inbox.sh` if relevant. No bulk session edits without user OK unless `required`.

## Rules

- Only `./scripts/hub-upgrade.sh` refreshes hub-root scripts/hooks/docs
- Never delete `repos/` or session history
- Product work stays in worktrees
