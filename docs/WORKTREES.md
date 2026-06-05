# Git worktrees (monorepo sessions)

Each **product** session gets an isolated git checkout under `sessions/<codename>/worktrees/<task-id>/` on its own `feature_branch`. The hub root stays on `main` for orchestration; agents edit product code in the worktree only.

---

## Task schema (`session.json`)

```json
{
  "mode": "product",
  "tasks": [
    {
      "id": "main",
      "feature_branch": "session/alpha",
      "base_branch": "main",
      "status": "draft"
    }
  ]
}
```

| Field | Meaning |
|-------|---------|
| `id` | Worktree folder name under `worktrees/` |
| `feature_branch` | Branch created/checked out in the worktree |
| `base_branch` | Upstream branch (`origin/<base>` after fetch) |
| `worktree` | Filled by `ensure-worktrees.sh` — do not hand-edit |

---

## Commands

```bash
./scripts/new-session.sh [codename]     # creates session + default task
./scripts/ensure-worktrees.sh <name>    # git worktree add per task
$(cat .hub-launcher)                    # picker runs ensure-worktrees when .git exists
```

---

## Modes

| `mode` | Writable at hub root |
|--------|----------------------|
| `product` (default) | No — use `sessions/<codename>/worktrees/**` |
| `hub` | Yes — `scripts/`, `.cursor/`, docs (template maintenance) |

---

## Git layout

| Commit | Local only (`.gitignore`) |
|--------|---------------------------|
| `sessions/_template/`, `sessions/_codenames.example.yaml`, `sessions/index.example.json` | `sessions/<codename>/` (entire tree) |
| `docs/WORKTREES.md`, `scripts/ensure-worktrees.sh` | `sessions/*/worktrees/*` |
| | `sessions/index.json`, `sessions/_codenames.yaml` |
| | `sessions/bindings/`, `sessions/context/`, `sessions/_inbox/*.md` |

Copy examples on first `new-session.sh` if local index/codenames are missing.

---

## Merge flow

1. Work and commit on `session/<codename>` inside the worktree.
2. Push branch; open PR to `main`.
3. After merge: remove worktree (`git worktree remove …`) and mark session completed.

No JIRA tickets or multi-repo `repos/` — single monorepo at hub root.
