# Sessions

Parallel Cursor chats → **codenames** under `sessions/<codename>/`.

**Quick links:** [AGENTS.md](AGENTS.md) · [docs/REPOS.md](docs/REPOS.md) · `sessions/<codename>/BOUNDARIES.md`

---

## Concepts

| Term | Meaning |
|------|---------|
| **Codename** | Short name for one unit of work (`sessions/<codename>/`) |
| **Binding** | Link between *this chat* or *this tmux pane* and a codename |
| **Worktree** | Writable checkout at `sessions/<codename>/worktrees/<repo>/` (from `repos.yaml`) |
| **Reference clone** | Read-only `repos/<repo>/` — refresh via `clone-repos.sh` |
| **Canonical metadata** | `sessions/<codename>/session.json` — title, mode, tasks, status, optional `next`; tasks may include `pr`, `ci`, `note` |
| **Derived metadata** | `sessions/index.json`, `sessions/context/*.md`, `progress.json` |

There is **no global active session**. Each chat/tab resolves its own codename.

---

## Resolution order

1. **Cursor chat binding** — `sessions/bindings/<conversation_id>.json` (`WORKSPACE_CONVERSATION_ID`)
2. **tmux pane** — `@workspace-codename` on this pane (`WORKSPACE_TMUX_PANE_OPTION`)
3. **tmux session** — exactly one codename on sibling tabs → inherit
4. **tmux window name** — renamed to `{prefix}{codename}` (default prefix from hub slug; override with `WORKSPACE_TMUX_WINDOW_PREFIX`; set to empty to disable)

Project launcher (see `.hub-launcher`) shows the interactive picker by default. Use `<launcher> --reuse` to skip when already bound.

---

## What gets updated when

### Pick or bind (project launcher, `bind-session.sh`)

| File | Update |
|------|--------|
| `sessions/bindings/<id>.json` | Chat → codename |
| `sessions/context/<id>.md` | Refreshed from `session.json` + `TASKS.md` + worktrees |
| `session.json` | `status` → `active`; clears `ended` / `paused_at` |
| `sessions/index.json` | Synced from `session.json` (local) |
| `progress.json` | `status` → `active`, `last_bound_at` |
| tmux | Pane option set; window renamed |
| worktrees | Launcher runs `clone-repos.sh` + `ensure-worktrees.sh` when `repos.yaml` exists |

### Create new (`new-session.sh` + bind)

New directory from `sessions/_template/` (`tasks: []` + `worktrees/`), codename marked used in local `_codenames.yaml`.

### Edit scope / tasks

Update **`session.json`** and **`TASKS.md`**, then:

```bash
./scripts/ensure-worktrees.sh <codename>   # after task changes
./scripts/sync-session.sh <codename>
```

Optional **`session.json`** fields (synced into context on bind):

| Field | Purpose |
|-------|---------|
| `next` | One-line resume hint (session picker + chat context) |
| `tasks[].pr` | Pull request URL |
| `tasks[].ci` | CI/build URL |
| `tasks[].note` | Free-text task status |

---

## GitHub fork workflow (optional)

When `repos.yaml` sets `github_fork_user` and `remote: github` on a repo entry:

- `clone-repos.sh` / `ensure-worktrees.sh` configure **origin** (upstream fetch) + **fork** (push default)
- Repair remotes: `./scripts/configure-git-remotes.sh [alias]`
- Agent rule: `.cursor/rules/git-fork-pr.mdc`

Details: [docs/REPOS.md](docs/REPOS.md).

### End session (`end-session.sh`)

Marks completed; clears **this chat's** binding only. Session folder and worktree stay on disk.

---

## Status lifecycle

`draft` → `active` → `paused` → `completed`

Canonical status lives in `session.json`. Run `sync-session.sh` if local `index.json` drifts.

---

## Commands

| Command | Purpose |
|---------|---------|
| `./scripts/repos-status.sh` | Agent bootstrap state (missing/empty/needs_clone/ready) |
| `./scripts/hub-status.sh` | Installed vs upstream template version (JSON; `--cached-only` skips fetch) |
| `./scripts/hub-upgrade.sh` | Refresh hub scripts/hooks/docs in place (`--dry-run`, `--yes`, `--to VERSION`, `--allow-untrusted-upstream`) |
| `<launcher>` (`.hub-launcher`) | Session list → bind → clone/worktrees when ready → agent CLI |
| `./scripts/resolve-session.sh` | Print codename for this chat/tab |
| `./scripts/bind-session.sh <name>` | Bind + resume |
| `./scripts/clone-repos.sh` | Clone/update reference repos from `repos.yaml` |
| `./scripts/configure-git-remotes.sh [alias]` | Repair upstream/fork remotes (GitHub fork workflow) |
| `./scripts/generate-workspace.sh [path]` | Write multi-root `.code-workspace` from `repos.yaml` |
| `./scripts/ensure-worktrees.sh <name>` | Create git worktrees from `session.json` tasks |
| `./scripts/sync-session.sh [name]` | Sync index/context from `session.json` |
| `./scripts/unbind-session.sh` | Clear binding only |
| `./scripts/end-session.sh [name]` | Close work + unbind this chat |
| `./scripts/list-active-sessions.sh` | Table of open sessions |
| `./scripts/prompt-session-start.sh` | Agent-facing picker text |
| `./scripts/new-session.sh [name]` | Create new codename directory |
| `./scripts/rename-tmux-session.sh [name]` | Rename tmux window |
| `./scripts/session-inbox.sh write/read` | Cross-session messages |

Implementation: `scripts/lib/session_binding.py` + `scripts/lib/session_cli.py`.

---

## tmux workflow

```text
Tab 1: my-agent → pick alpha  →  worktree sessions/alpha/worktrees/project, window alpha
Tab 2: my-agent --reuse       →  reuses alpha (picker skipped)
Tab 3: my-agent → pick bravo  →  separate branch + worktree
```

---

## Cursor chat workflow

1. **start work** / `/start-work` — orchestrator lists sessions, you pick codename or **new**
2. Agent runs `./scripts/bind-session.sh <codename>`
3. Hooks inject `sessions/context/<conversation_id>.md` on session start
4. **end session** — skill runs `./scripts/end-session.sh` (not the before-prompt hook)

Do **not** run bare `agent` in tmux — use the project launcher so hooks and session resolution run.

---

## Cross-session inbox

Session **A** leaves a note for session **B** without copy-paste between Cursor windows.

| Action | Command |
|--------|---------|
| **Write** | `./scripts/session-inbox.sh write bravo alpha "your message"` |
| **Read** | `./scripts/session-inbox.sh read alpha` |
| **Auto** | On bind, `sessions/_inbox/<codename>.md` is injected into `sessions/context/<chat>.md` |

Files live in `sessions/_inbox/` (shared; any session may write via the script). See [sessions/_inbox/README.md](sessions/_inbox/README.md).

---

## Git — committed vs local

| Commit | Do not commit (see `.gitignore`) |
|--------|----------------------------------|
| `scripts/`, `.cursor/`, `SESSIONS.md`, `docs/REPOS.md`, `docs/PROJECT.md.example`, `repos.yaml.example`, `.hub-version`, `.hub-upstream.example` | `repos.yaml`, `repos/*` — your clone URLs + reference repos |
| `sessions/_template/`, `sessions/_codenames.example.yaml`, `sessions/index.example.json` | `sessions/<codename>/`, `sessions/*/worktrees/*` |
| | `docs/PROJECT.md` — your project coding guidelines |
| | `sessions/index.json`, `sessions/_codenames.yaml` — local index |
| | `sessions/bindings/`, `sessions/context/` — per-chat bindings |
| | `sessions/_inbox/*.md` — inbox bodies |
| | `sessions/<codename>/reviews/`, `checkpoints.json` — local review/checkpoint artifacts |
| | `.hub-upstream`, `.hub-upstream-cache/`, `.hub-upgrade-staging/` — upstream override and upgrade cache |
| | `.hub-launcher`, `.hub-slug` — local install paths |
| | `*.code-workspace` — generated editor workspace |

Track milestones in product `CURRENT.md` instead of committing `progress.json`.

When you add a Node monorepo, uncomment the `node_modules/` block in `.gitignore` or merge your app ignores.
