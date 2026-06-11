# Project guidelines

Generic **hub template** project guidelines. Read together with:

- **Level 1 (template):** [`.cursor/rules/agent-guidelines.mdc`](../.cursor/rules/agent-guidelines.mdc)
- **Agent entry:** [AGENTS.md](../AGENTS.md) · bound session `BOUNDARIES.md`

---

## Stack

| Layer | Choice |
|-------|--------|
| Language / runtime | TypeScript 5, Node 20 |
| Package manager | pnpm workspaces |
| Linter / formatter | ESLint + tsc |
| Branch naming | `feat/`, `fix/`, `docs/` |
| Test command | `pnpm --filter @immo/api test` · `pnpm --filter @immo/web build` |

---

## Doc sync map

When code changes, update these docs in the **same PR**:

| Change type | Update |
|-------------|--------|
| New API route | `CHANGELOG.md` (Added), `CURRENT.md` web routes table, `ARCHITECTURE.md` if new resource |
| New web page / route | `CHANGELOG.md` (Added), `CURRENT.md` web routes table |
| New DB query or helper (`packages/db`) | `CHANGELOG.md` (Added), plan doc task status row |
| DTO change | `CHANGELOG.md` (Changed/Added), `docs/ARCHITECTURE.md` if data model changes |
| Milestone sub-task done | `CURRENT.md` milestone table + decision log entry, `docs/M*-PLAN.md` task row |
| Schema / migration | migration comment, `docs/ARCHITECTURE.md`, `docs/DATA-MODEL-RFC.md` |
| Domain rule or formula | `packages/domain` doc + golden fixture README |
| Config or env var | worktree `README.md`, `.env.example` |
| Hub script or session field | [AGENTS.md](../AGENTS.md), [SESSIONS.md](../SESSIONS.md), relevant skill |

---

## Layout (immo monorepo)

| Path | Purpose |
|------|---------|
| `apps/api/src/routes/` | Express route handlers |
| `apps/api/src/dto/` | DTO types + `toSafeDto` helpers |
| `apps/web/src/pages/` | React page components |
| `apps/web/src/components/` | Shared presentational components |
| `apps/web/src/api/` | API client + TypeScript types |
| `packages/db/src/queries/` | Prisma query functions |
| `packages/domain/` | Screening math (Out, Gap, Mietspiegel) |
| `workers/` | ingest · analytics · screening batch |
| `docs/` | ROADMAP, ARCHITECTURE, M*-PLAN, DATA-MODEL-RFC, CURRENT |
| `CHANGELOG.md` | All notable changes (unreleased at top) |
| `CURRENT.md` | Milestone status + web routes + decision log |

---

## Test minimum

Before opening a product PR from a worktree:

```bash
cd sessions/<codename>/worktrees/immo
pnpm --filter @immo/api test
pnpm --filter @immo/web build
```

| Change type | Minimum test |
|-------------|--------------|
| Domain logic | unit test or golden fixture in `packages/domain` |
| DB query | `packages/db` test with seeded fixture |
| API route | route test + error/null path |
| Web component | `pnpm --filter @immo/web build` exits 0, no TS errors |

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
