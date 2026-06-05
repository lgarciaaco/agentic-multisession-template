# Repos registry (`repos.yaml`)

Hub = orchestration (`sessions/`, `scripts/`, `.cursor/`). Product code lives in **registered repos** under `repos/` (reference clones) and **session worktrees** (writable).

**One product repo** = `repos.yaml` with a single entry. No separate “monorepo layout” — same model as art, N=1.

---

## Layout

```text
hub-root/
  repos.yaml              # registry (copy from repos.yaml.example)
  repos/                  # reference clones (gitignored)
    project/              # one entry → one folder
  sessions/
    alpha/
      worktrees/
        project/          # writable checkout on feature_branch
```

---

## `repos.yaml`

```yaml
repos:
  project:
    path: repos/project
    clone: git@github.com:YOU/PROJECT.git
    default_branch: main
```

| Field | Meaning |
|-------|---------|
| Key (`project`) | Alias used in `session.json` → `tasks[].repo` |
| `path` | Reference clone directory (`repos/<name>`) or `.` for hub-only |
| `clone` | Remote URL (`clone-repos.sh`) |
| `default_branch` | Branch to track and branch worktrees from |

Add a second key when you add a second repo (e.g. `flet-app`). Flet in the same git remote stays one `project` entry.

---

## Task schema (`session.json`)

```json
{
  "tasks": [
    {
      "id": "main",
      "repo": "project",
      "feature_branch": "session/alpha",
      "base_branch": "main",
      "status": "draft"
    }
  ]
}
```

`repo` must match a key in `repos.yaml`. Worktree path: `sessions/<codename>/worktrees/<repo>/`.

---

## Commands

```bash
cp repos.yaml.example repos.yaml    # once — set clone URL
./scripts/clone-repos.sh            # reference clones under repos/
./scripts/new-session.sh [codename]
./scripts/ensure-worktrees.sh <name>
```

Launcher runs `clone-repos` + `ensure-worktrees` when `repos.yaml` exists.

---

## Git — committed vs local

| Commit | Local (`.gitignore`) |
|--------|----------------------|
| `repos.yaml.example` | `repos.yaml` (your URLs) |
| `docs/REPOS.md`, `scripts/clone-repos.sh` | `repos/*` |
| | `sessions/<codename>/`, `worktrees/*` |

---

## Guards

- **`repos/`** — read-only (hook denies edits)
- **`sessions/<codename>/worktrees/`** — writable product code
- **Hub root** — allowed (scripts, docs); product agents should still use worktrees

No JIRA, tickets, or fork remotes in the generic template.
