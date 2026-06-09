# Contributing

This repository is a **generic template** for multi-session Cursor agent hubs. Contributions should improve the skeleton only — no project-specific domain logic.

## Using the template

1. Click **Use this template** on GitHub (or copy the repo)
2. Follow [CUSTOMIZE.md](CUSTOMIZE.md) to bootstrap your hub

## Where to edit

See [docs/REPOS.md](docs/REPOS.md) (Guards + Self-hosted hub): product work in session worktrees; hub-root hook-blocked when bound; registry pins unbound-only; hub refresh via `./scripts/hub-upgrade.sh`.

## Pull requests

- Keep examples generic (`my-app`, `my-agent`) — no real project names
- Open from a session worktree branch, not from hub root `main`; wait for CI (`test` workflow) to pass
- Run `python3 scripts/test_session_binding.py`, `python3 scripts/test_git_remotes.py`, and `python3 scripts/test_hub_upgrade.py` before opening a PR
- Scope: session binding, repos registry, worktrees, hooks, docs, install — not domain features
- **Do not** use `gh pr merge --auto` or enable auto-merge on the repo
- **Do not** merge PRs unless the maintainer explicitly asks — user merges on GitHub, or asks for `gh pr merge <n> --merge` (without `--auto`)

## Report issues

Open a GitHub issue with steps to reproduce and your environment (Cursor version, Python, tmux if relevant).
