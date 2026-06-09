---
name: bootstrap-hub
description: Agent-first hub bootstrap after cloning agentic-multisession-template. Detect state, ask user for repos, run scripts.
---

# Bootstrap hub (agent-first)

**Entry:** user cloned template, `cd` into hub, started agent. **You** bootstrap — do not hand the user a manual checklist unless they ask.

Triggers: first chat in fresh hub, `bootstrap hub`, `set up template`, `customize template`

---

## 1. Detect state

```bash
./scripts/repos-status.sh
```

| `state` | Meaning | You do |
|---------|---------|--------|
| `no_repos_yaml` | No registry yet | **Ask user** for repos (see below). Create `repos.yaml` from `repos.yaml.example`. |
| `empty_registry` | `repos: {}` | **Ask user** what to add. Edit `repos.yaml`, then `clone-repos.sh`. |
| `needs_clone` | URLs set, not cloned | Run `./scripts/clone-repos.sh` (or ask user to fix URLs if it fails). |
| `ready` | Reference clones exist | Session + worktree flow; skip repo questions unless user adds more. |

Also run `hub_setup_remaining` from status JSON if present (pip + `install-workspace-agent.sh`).

---

## 2. Ask user (required when `no_repos_yaml` or `empty_registry`)

Do **not** invent clone URLs. Ask:

> Which product repos should this hub track? For each: **alias** (short name), **git clone URL**, **default branch** (usually `main`).

User may say:
- **None yet** — sessions only until repos are registered. Leave `repos: {}`; no `clone-repos` until they add repos. (While unbound, agents may edit hub root for bootstrap; after bind, product work uses worktrees.)
- **One repo** — e.g. `project` → one `repos.yaml` entry, `path: repos/<alias>`.
- **Several** — one entry per remote.

Write `repos.yaml`:

```yaml
repos:
  <alias>:
    path: repos/<alias>
    clone: <url>
    default_branch: main
```

Then `./scripts/clone-repos.sh`.

### Self-hosted hub (template editing itself)

When the user develops **this hub repo** as the product (same clone URL as hub `origin`):

- See [docs/REPOS.md](../../../docs/REPOS.md) Self-hosted hub (`path: repos/<alias>`, not `path: .`; worktrees for product edits).
- `repos-status.sh` reports `self_hosted: true` when a registry clone URL matches hub origin.

---

## 2b. Codename theme (optional)

When the user cares about session naming, ask:

> Do you want a codename theme for new sessions? Default is NATO (`alpha`, `bravo`, …). Example: `bg3` uses companion names from [`sessions/_codenames.example.yaml`](../../../sessions/_codenames.example.yaml).

If they choose a theme:

1. Ensure `sessions/_codenames.yaml` exists (created on first `new-session.sh`, or copy from example).
2. Set `active_pool: <theme>` and confirm the pool exists under `pools:` (add custom names if needed).

Pools **auto-expand** with NATO continuation (`india`, `juliet`, …) when all names are used — no manual yaml edits required.

---

## 3. User adds a repo later

When user says “add repo X” / “clone … into repos”:

1. Add entry to `repos.yaml` (alias, path, clone, default_branch).
2. `./scripts/clone-repos.sh`
3. If a session should use it: add task in `sessions/<codename>/session.json` with `"repo": "<alias>"`, then `./scripts/ensure-worktrees.sh <codename>`.

Never `git clone` manually into `repos/` unless `clone-repos.sh` cannot run — prefer the script.

---

## 4. Hub naming (when user cares)

Update `README.md` / `AGENTS.md` with project name while **unbound** (hub-root edits blocked after session bind); shorten template-bootstrap block in `AGENTS.md` when done.

`python3 scripts/test_session_binding.py` — must pass.

---

## Rules

- Work in **this hub only** unless user points at another path.
- Product code: `sessions/<codename>/worktrees/<repo>/` — not `repos/` (read-only).
- Do not add domain features unless user specifies purpose.
