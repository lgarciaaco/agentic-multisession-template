# Repos registry (`repos.yaml`)

Hub = orchestration (`sessions/`, `scripts/`, `.cursor/`). Product code lives in **registered repos** under `repos/` (reference clones) and **session worktrees** (writable).

**One product repo** = `repos.yaml` with a single entry (multi-repo registry with N=1).

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
  <hub-slug>.code-workspace   # optional — ./scripts/generate-workspace.sh
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

Add a second key when you add a second repo (e.g. `web-ui`). Code in the same git remote stays one `project` entry.

### Optional: GitHub fork workflow

When you contribute via a personal fork of an org repo:

```yaml
github_fork_user: YOUR_GITHUB_USER

repos:
  upstream-app:
    path: repos/upstream-app
    clone: git@github.com:ORG/upstream-app.git
    remote: github
    name: upstream-app
    default_branch: main
```

| Field | Meaning |
|-------|---------|
| `github_fork_user` | Top-level default GitHub user for fork URLs |
| `remote: github` | Enable fork workflow for this entry |
| `name` | Repo name on GitHub (for derived fork URL) |
| `fork` | Explicit fork clone URL (overrides derived URL) |
| `fork_user` | Per-repo fork user (overrides `github_fork_user`) |
| `remote: gitlab` | Push to `origin` only (no fork remote) |

`clone-repos.sh` and `ensure-worktrees.sh` configure remotes automatically. Repair with `./scripts/configure-git-remotes.sh [alias]`.

See `.cursor/rules/git-fork-pr.mdc` when using fork workflow.

---

## Session schema (`session.json`)

```json
{
  "title": "",
  "status": "draft",
  "next": "One-line next step for resume/handoff",
  "tasks": [
    {
      "id": "main",
      "repo": "project",
      "feature_branch": "session/alpha",
      "base_branch": "main",
      "status": "draft",
      "pr": "https://github.com/ORG/project/pull/123",
      "ci": "https://ci.example.com/job/123",
      "note": "Free text — links, merge SHA, blockers"
    }
  ]
}
```

| Field | Meaning |
|-------|---------|
| `next` | Optional resume hint (shown in session picker and chat context) |
| `tasks[].pr` | Pull request URL when it exists |
| `tasks[].ci` | CI/build URL (any provider) |
| `tasks[].note` | Free-text task status |

`repo` must match a key in `repos.yaml`. Worktree path: `sessions/<codename>/worktrees/<repo>/`.

---

## Guidelines (optional)

Template rules live in `.cursor/rules/agent-guidelines.mdc` (always applied). Each hub may add project-specific docs:

| File | Role |
|------|------|
| [docs/PROJECT.md.example](../docs/PROJECT.md.example) | Committed scaffold — copy to `docs/PROJECT.md` (local) |
| `docs/PROJECT.md` | Project doc sync map, test commands, stack conventions |
| Worktree `CONTRIBUTING.md` | Product PR flow in primary worktree |

Optional pointers in `repos.yaml`:

```yaml
guidelines:
  project: docs/PROJECT.md       # canonical hub-relative path
  # doc: docs/PROJECT.md        # alias for project (accepted)
  worktree: CONTRIBUTING.md      # relative to primary worktree root
```

| Key | Meaning |
|-----|---------|
| `project` | Hub-relative path to project guidelines (canonical) |
| `doc` | Alias for `project` |
| `worktree` | Path relative to primary worktree root (e.g. `CONTRIBUTING.md`) |

On session bind, `sessions/context/<chat>.md` lists which guideline files exist. See [AGENTS.md](../AGENTS.md) **Coding guidelines**.

---

## Agent-first bootstrap

User clones template and starts the agent. Agent runs:

```bash
./scripts/repos-status.sh
```

- **`no_repos_yaml` / `empty_registry`** → agent **asks** user for alias + clone URL + branch per repo, writes `repos.yaml`
- **`needs_clone`** → `./scripts/clone-repos.sh`
- **`ready`** → sessions + worktrees

User may add repos later (“add web-ui repo”) → agent edits `repos.yaml`, `clone-repos`, optional `ensure-worktrees`.

## Commands

```bash
./scripts/repos-status.sh              # agent: what to do next
./scripts/clone-repos.sh               # after repos.yaml filled
./scripts/configure-git-remotes.sh     # repair fork/upstream remotes
./scripts/generate-workspace.sh        # multi-root .code-workspace for Cursor/VS Code
./scripts/new-session.sh [codename]
./scripts/set-session-scope.sh [name] --title T [--goal G] [--next N]
./scripts/ensure-worktrees.sh <name>   # after tasks[].repo set
```

Launcher runs `clone-repos` + `ensure-worktrees` when `repos.yaml` exists and status is past empty.

---

## Git — committed vs local

| Commit | Local (`.gitignore`) |
|--------|----------------------|
| `repos.yaml.example` | `repos.yaml` (your URLs) |
| `docs/REPOS.md`, `scripts/clone-repos.sh` | `repos/*` |
| `docs/PROJECT.md.example` | `docs/PROJECT.md` (your project guidelines) |
| | `sessions/<codename>/`, `worktrees/*` |
| | `*.code-workspace` (generated locally) |

---

## Self-hosted hub

When the hub **is** the product (registry clone URL matches hub `origin` — `repos-status.sh` → `self_hosted: true`):

```yaml
repos:
  template:
    path: repos/template          # reference clone (required — not path: .)
    clone: git@github.com:YOU/agentic-multisession-template.git
    default_branch: main
```

```text
sessions/<codename>/worktrees/template/   # feature branch — all product edits here
sessions/<codename>/                      # session metadata when bound
hub root (main)                           # hook-blocked when bound; refresh via ./scripts/hub-upgrade.sh only
```

- `path: .` is for fetch-only registry entries, not development worktrees (git nesting limit).
- Hub-root `scripts/`, `.cursor/`, docs, and registry pins (`repos.yaml`, `.hub-version`, `.hub-upstream`) are **hook-blocked** for bound sessions — edit pins only when unbound.
- Refresh hub layer: `./scripts/hub-upgrade.sh` only.

---

## Guards

- **`repos/`** — read-only (hook denies edits)
- **`sessions/<codename>/worktrees/`** — writable product code
- **Hub root product paths** — blocked for bound sessions (`scripts/`, `.cursor/`, `docs/`, root markdown)
- **Hub root** — blocked for bound sessions (including `repos.yaml`, `.hub-version`, `.hub-upstream`); registry pins unbound-only
