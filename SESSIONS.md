# Sessions

Parallel Cursor chats → **codenames** under `sessions/<codename>/`.

**Quick links:** [AGENTS.md](AGENTS.md) · `sessions/<codename>/BOUNDARIES.md`

---

## Concepts

| Term | Meaning |
|------|---------|
| **Codename** | Short name for one unit of work (`sessions/<codename>/`) |
| **Binding** | Link between *this chat* or *this tmux pane* and a codename |
| **Canonical metadata** | `sessions/<codename>/session.json` — title, tasks, status |
| **Derived metadata** | `sessions/index.json`, `sessions/context/*.md`, `progress.json` |

There is **no global active session**. Each chat/tab resolves its own codename.

---

## Resolution order

1. **Cursor chat binding** — `sessions/bindings/<conversation_id>.json` (`WORKSPACE_CONVERSATION_ID`)
2. **tmux pane** — `@workspace-codename` on this pane (`WORKSPACE_TMUX_PANE_OPTION`)
3. **tmux session** — exactly one codename on sibling tabs → inherit
4. **tmux window name** — when renamed to an active codename (optional `WORKSPACE_TMUX_WINDOW_PREFIX`)

Project launcher (see `.hub-launcher`) shows the interactive picker by default. Use `<launcher> --reuse` to skip when already bound.

---

## What gets updated when

### Pick or bind (project launcher, `bind-session.sh`)

| File | Update |
|------|--------|
| `sessions/bindings/<id>.json` | Chat → codename |
| `sessions/context/<id>.md` | Refreshed from `session.json` + `TASKS.md` |
| `session.json` | `status` → `active`; clears `ended` / `paused_at` |
| `sessions/index.json` | Synced from `session.json` |
| `progress.json` | `status` → `active`, `last_bound_at` |
| tmux | Pane option set; window renamed |

### Create new (`new-session.sh` + bind)

New directory from `sessions/_template/`, codename marked used in `_codenames.yaml`.

### Edit scope / tasks

Update **`session.json`** and **`TASKS.md`**, then:

```bash
./scripts/sync-session.sh <codename>
```

### End session (`end-session.sh`)

Marks completed; clears **this chat's** binding only. Session folder stays on disk.

---

## Status lifecycle

`draft` → `active` → `paused` → `completed`

Canonical status lives in `session.json`. Run `sync-session.sh` if `index.json` drifts.

---

## Commands

| Command | Purpose |
|---------|---------|
| `<launcher>` (`.hub-launcher`) | Session list → bind → Cursor agent CLI |
| `./scripts/resolve-session.sh` | Print codename for this chat/tab |
| `./scripts/bind-session.sh <name>` | Bind + resume |
| `./scripts/sync-session.sh [name]` | Sync index/context from `session.json` |
| `./scripts/unbind-session.sh` | Clear binding only |
| `./scripts/end-session.sh [name]` | Close work + unbind this chat |
| `./scripts/list-active-sessions.sh` | Table of open sessions |
| `./scripts/prompt-session-start.sh` | Agent-facing picker text |
| `./scripts/new-session.sh [name]` | Create new codename directory |
| `./scripts/rename-tmux-session.sh [name]` | Rename tmux window |

Implementation: `scripts/lib/session_binding.py` + `scripts/lib/session_cli.py`.

---

## tmux workflow

```text
Tab 1: my-agent → pick alpha  →  window alpha, @workspace-codename=alpha
Tab 2: my-agent --reuse       →  reuses alpha (picker skipped)
Tab 3: my-agent → pick bravo  →  separate codename
```

---

## Cursor chat workflow

1. **start work** / `/start-work` — orchestrator lists sessions, you pick codename or **new**
2. Agent runs `./scripts/bind-session.sh <codename>`
3. Hooks inject `sessions/context/<conversation_id>.md` on session start
4. **end session** — skill runs `./scripts/end-session.sh` (not the before-prompt hook)

Do **not** run bare `agent` in tmux — use the project launcher so hooks and session resolution run.

---

## Git — committed vs local

| Commit | Do not commit (see `.gitignore`) |
|--------|----------------------------------|
| `scripts/`, `.cursor/`, `SESSIONS.md`, `sessions/_template/`, `sessions/_codenames.yaml` | `sessions/bindings/` — per-chat bindings |
| `sessions/<codename>/` — `TASKS.md`, `session.json`, `BOUNDARIES.md` | `sessions/context/` — derived per conversation |
| `sessions/index.json` (synced from `session.json`) | `.hub-launcher`, `.hub-slug` — local install paths |

**Optional:** omit `sessions/*/progress.json` if you want less churn; track milestones in product `CURRENT.md` instead.

When you add a Node monorepo, uncomment the `node_modules/` block in `.gitignore` or merge your app ignores.
