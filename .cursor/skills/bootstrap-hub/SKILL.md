---
name: bootstrap-hub
description: Agent-first hub bootstrap after cloning agentic-multisession-template. Detect state, ask user for repos, run scripts.
---

# Bootstrap hub

**Entry:** user cloned template, started agent. Agent drives bootstrap.

Triggers: first chat, `bootstrap hub`, `set up template`

## 1. Detect state

```bash
./scripts/repos-status.sh
```

| `state` | Action |
|---------|--------|
| `no_repos_yaml` / `empty_registry` | Ask user for alias + clone URL + branch; write `repos.yaml`; `clone-repos.sh` |
| `needs_clone` | `./scripts/clone-repos.sh` |
| `ready` | Session + worktree flow |

Run `hub_setup_remaining` from JSON if present (`pip install -r scripts/requirements.txt`, `./scripts/install-workspace-agent.sh`).

## 2. Repos

Do not invent URLs. Hub-only (`repos: {}`) is valid until user adds repos.

Self-hosted: register hub at `repos/<alias>`; product edits in worktrees. See [docs/REPOS.md](../../../docs/REPOS.md).

Optional codename theme: `sessions/_codenames.yaml` — see [sessions/_codenames.example.yaml](../../../sessions/_codenames.example.yaml).

## 3. Add repo later

Edit `repos.yaml` → `clone-repos.sh` → task `"repo": "<alias>"` in `session.json` → `ensure-worktrees.sh`.

Prefer `clone-repos.sh` over manual `git clone`.

## Rules

- Product code: `sessions/<codename>/worktrees/<repo>/` — `repos/` read-only
- No domain features unless user specifies
- Skill edits: load [skill-optimizer](../skill-optimizer/SKILL.md)
