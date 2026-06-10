# Project guidelines

Generic **hub template** project guidelines. Read together with:

- **Level 1 (template):** [`.cursor/rules/agent-guidelines.mdc`](../.cursor/rules/agent-guidelines.mdc)
- **Agent entry:** [AGENTS.md](../AGENTS.md) · bound session `BOUNDARIES.md`

Copy [docs/PROJECT.md.example](PROJECT.md.example) over this file and fill in your stack when you customize the hub for a product.

---

## Doc sync map

When code changes, update these docs in the **same PR**:

| Change type | Update |
|-------------|--------|
| New API endpoint | API doc under `docs/`, worktree README |
| Schema / migration | migration comment, architecture doc under `docs/` |
| Domain rule or formula | domain doc + golden fixture README |
| Config or env var | README, `.env.example` in worktree |
| Hub script or session field | [AGENTS.md](../AGENTS.md), [SESSIONS.md](../SESSIONS.md), relevant skill — see [agent-guidelines.mdc](../.cursor/rules/agent-guidelines.mdc) |

Add project-specific rows when you customize.

---

## Layout

Document where code belongs. Structure reviewer checks new/changed files against this map.

| Path | Purpose |
|------|---------|
| `src/` or `packages/` | Application source (adjust to your stack) |
| `tests/` or `**/*.test.*` | Tests colocated or mirrored |
| `scripts/` | CLI and automation (if applicable) |
| `.cursor/skills/` | Hub agent skills (self-hosted template only) |
| `docs/` | Committed hub or product documentation |

Product code for a registered repo lives in `sessions/<codename>/worktrees/<repo>/` — not `repos/` (reference clones, read-only).

---

## Test minimum

Before opening a product PR from a worktree:

```bash
cd sessions/<codename>/worktrees/<repo>
# Replace with your stack, e.g.:
# pnpm test && pnpm build
# pytest, cargo test, etc.
```

| Change type | Minimum test |
|-------------|--------------|
| Domain logic | unit test or golden fixture |
| API route | validation test + error path |
| Docker / env | smoke command documented in README |

**Hub template PRs** (when `session.json` has `"mode": "hub"`): see [CONTRIBUTING.md](../CONTRIBUTING.md) and `.cursor/rules/hub-contributing.mdc`.

---

## Stack conventions

Fill per project when you customize:

- **Language / runtime:** (e.g. TypeScript 5, Python 3.12)
- **Package manager:** (e.g. pnpm, pip)
- **Linter / formatter:** (e.g. eslint, ruff)
- **Branch naming:** (e.g. `feat/`, `fix/`)

---

## Worktree PR flow

Product code lives in `sessions/<codename>/worktrees/<repo>/`.

See **CONTRIBUTING.md** in the worktree (or hub root when unbound) for PR conventions. When `repos.yaml` sets GitHub fork workflow, push feature branches to **`fork`** — see [docs/REPOS.md](REPOS.md) and `.cursor/rules/git-fork-pr.mdc`.

Optional in `repos.yaml`:

```yaml
guidelines:
  project: docs/PROJECT.md
  worktree: CONTRIBUTING.md
```
