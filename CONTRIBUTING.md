# Contributing

This repository is a **generic template** for multi-session Cursor agent hubs. Contributions should improve the skeleton only — no project-specific domain logic.

## Using the template

1. Click **Use this template** on GitHub (or copy the repo)
2. Follow [CUSTOMIZE.md](CUSTOMIZE.md) to bootstrap your hub

## Pull requests

- Keep examples generic (`my-app`, `my-agent`) — no real project names
- Run `python3 scripts/test_session_binding.py` and `python3 scripts/test_hub_upgrade.py` before opening a PR
- Scope: session binding, repos registry, worktrees, hooks, docs, install — not domain features
- Open PRs from feature branches; wait for CI (`test` workflow) to pass
- **Do not** use `gh pr merge --auto` or enable auto-merge on the repo
- **Do not** merge PRs unless the maintainer explicitly asks — user merges on GitHub, or asks for `gh pr merge <n> --merge` (without `--auto`)

## Report issues

Open a GitHub issue with steps to reproduce and your environment (Cursor version, Python, tmux if relevant).
