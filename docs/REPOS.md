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
| `pr_target_branch` | Optional PR base branch (falls back to `default_branch`) |

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

`./scripts/clone-repos.sh` and `./scripts/ensure-worktrees.sh` configure remotes automatically. Repair with `./scripts/configure-git-remotes.sh [alias]`.

`file://` clone URLs are rejected by default (`validate_clone_url`); set `WORKSPACE_ALLOW_FILE_CLONES=1` only for local debugging.

### Trusted clone hosts (opt-in)

By default, `validate_clone_url` checks URL shape and injection patterns only — it does **not** block hosts. To enforce a host allowlist for `repos.yaml` clone URLs (used by `clone-repos.sh`, `configure-git-remotes.sh`, and worktree setup):

| Variable | Purpose |
|----------|---------|
| `WORKSPACE_ENFORCE_CLONE_HOST_ALLOWLIST=1` | Enable host allowlist enforcement |
| `WORKSPACE_CLONE_HOST_ALLOWLIST` | Comma-separated extra hosts (e.g. `git.example.com,github.enterprise.com`) |

When enforcement is enabled, allowed hosts are **`github.com`**, **`gitlab.com`**, plus any entry in `WORKSPACE_CLONE_HOST_ALLOWLIST`. Other hosts raise `ValueError` naming the disallowed host. Allowlist entries must be plain hostnames (no ports or paths); values are normalized to lowercase.

**Production recommendation:** set `WORKSPACE_ENFORCE_CLONE_HOST_ALLOWLIST=1` (also accepts `true` or `yes`) in shared hub environments so `repos.yaml` clone URLs cannot target arbitrary hosts.

`hub_upgrade.py` uses a separate upstream trust check for template upgrades (`WORKSPACE_ALLOW_UNTRUSTED_UPSTREAM`); `clone-repos.sh` passes `--` before clone URLs so flag-like values cannot be parsed as git options.

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
./scripts/set-session-scope.sh [name] --title T [--goal G] [--next N]  # --goal also backfills empty progress.description
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
| | `sessions/<codename>/`, `sessions/*/worktrees/*` |
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
- **`.hub-upstream` override:** copy `.hub-upstream.example` → `.hub-upstream` at hub root when your install tracks a fork or mirror instead of the default template URL. One HTTPS URL per line (comments allowed in the example file only). Used by `./scripts/hub-status.sh` and `./scripts/hub-upgrade.sh` via `resolve_upstream_url()`. Same unbound-only rule as `repos.yaml` and `.hub-version`.
- Refresh hub layer: `./scripts/hub-upgrade.sh` only.

---

## Guards

### Writable when bound

- **`sessions/<codename>/worktrees/`** — product code

### Blocked when bound

- **`repos/`** — read-only (hook denies edits)
- **`sessions/_inbox/`** — direct path edits blocked; use `./scripts/session-inbox.sh write`
- **Hub root product paths** — `scripts/`, `.cursor/`, `docs/`, root markdown
- **Hub root** — including `repos.yaml`, `.hub-version`, `.hub-upstream`; registry pins unbound-only

**Limitations:** `beforeFileEdit` hooks constrain **Cursor file edits** only. Shell commands, terminal tools, and hub scripts can still read or write paths hooks block — workflow scripts validate session artifact paths in code for the same reason. Cross-session inbox messages are untrusted input: `write_inbox` sanitizes on write; `format_inbox_section` and `apply_plan_feedback` / `apply_brief_correction` sanitize on read before chat context or workflow artifacts. At workflow gates (`brief_review`, `plan_user_review`), `./scripts/sync-session.sh` may call `workflow-pull-inbox-gate.py --apply` before refreshing chat context — inbox gate auto-apply for gate commands is disabled (`gate_command_sender_authorized` returns false). **Program parent→child gate routing** uses `program-route-feedback.py` (tmux send-keys only); `write_inbox_program_route` is removed. **Inbox CLI caller auth:** bound sessions require `from` to match the bound codename (`--as` must match bound when used); unbound sessions require explicit `--as <codename>` matching `from` on every write. Bound and unbound sessions cannot edit `sessions/_inbox/` directly — use `./scripts/session-inbox.sh write`. Rejected inbox gate pulls are not marked processed — unauthorized blocks stay in `pending` until removed or an authorized path is used.
