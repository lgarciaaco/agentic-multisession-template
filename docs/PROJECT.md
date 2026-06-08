# immo-investor — project guidelines

Agent entry for **product** work in this hub. Read together with [AGENTS.md](../AGENTS.md) (sessions, scope, git) and the bound session's `BOUNDARIES.md`.

**Canonical code path:** `sessions/<codename>/worktrees/immo/` — not `repos/immo/` (reference clone, read-only).

---

## Doc sync map

When you change code, update the docs that describe that code in the **same PR**. Use this map — do not leave README or milestone tables stale.

Paths below are relative to the **product worktree** root.

| Change type | Update together |
|-------------|-----------------|
| **Screening / financing math** | `packages/domain/src/*.ts` · `docs/INVESTOR-TERMS.md` · `docs/CALCULATION-DEFAULTS.md` · golden fixtures in `packages/domain/src/*.test.ts` |
| **Prisma schema / migrations** | `packages/db/prisma/schema.prisma` · migration SQL comment (purpose + RFC section) · `docs/DATA-MODEL-RFC.md` · relevant section in `docs/M*.md` · `CURRENT.md` status table |
| **Ingest / lifecycle workers** | `workers/ingest/**` · `docs/M1-PLAN.md` sub-milestone table · `docs/ARCHITECTURE.md` if data-flow topology changes |
| **Analytics / Mietspiegel (M2+)** | worker or query code · `docs/M2-PLAN.md` · `docs/DATA-MODEL-RFC.md` |
| **API routes (M2+)** | `apps/api/**` · `docs/ARCHITECTURE.md` · route-level validation tests |
| **Web UI (M4+)** | `apps/web/**` · milestone plan doc · `docs/PRODUCT.md` if user-facing scope shifts |
| **New pnpm script / env var** | root `README.md` commands table · `.env.example` · `docs/M1-0-HANDOFF.md` (or handoff doc) if setup steps change |
| **Docker / local dev stack** | `docker/docker-compose.yml` · README quick start · smoke command below |
| **Milestone complete or re-scoped** | `docs/M*-PLAN.md` checklist · `CURRENT.md` · `docs/ROADMAP.md` if phase boundaries move |
| **Competitor / product scope** | `docs/PRODUCT.md` · `docs/MARKET-RESEARCH.md` |

Full product doc index: `docs/PRODUCT.md`.

---

## Test minimum

Run from the **worktree** root (`sessions/<codename>/worktrees/immo/`):

| Gate | Command | When |
|------|---------|------|
| **Required before PR** | `pnpm test` | Always — domain unit tests (vitest) |
| **Required before PR** | `pnpm build` | Always — all workspace packages compile |
| **Schema change** | `pnpm db:migrate` locally · `pnpm --filter @immo/db validate` | New or altered Prisma models |
| **Full workspace** | `pnpm test:all` | When touching stub packages or shared tooling |

**By change type:**

- **New domain logic** (`packages/domain`) — add or extend a unit test; prefer a **golden fixture** (fixed inputs → expected Out/Gap/Rate) aligned with `docs/INVESTOR-TERMS.md`. Existing reference: `screening.test.ts`, `financing.test.ts`, `defaults.test.ts`.
- **New API route** — validation test for happy path **and** at least one error path (400/404); no silent fallbacks for bad input.
- **New worker behavior** — unit test for pure helpers; integration smoke documented in milestone plan (e.g. M1-4: one buy URL + one rent URL → rows in DB).
- **Docker / env change** — document in README; smoke: `docker compose -f docker/docker-compose.yml up -d` then `pnpm db:migrate`.

Do not merge with failing tests or undocumented breaking changes to golden expected values — update docs and fixtures together.

---

## Stack conventions

| Area | Convention |
|------|------------|
| **Runtime** | Node ≥ 20 |
| **Monorepo** | pnpm workspaces — root scripts delegate to packages (`pnpm --filter @immo/domain …`) |
| **TypeScript** | `strict: true` in package tsconfigs; no `any` on **public** exports (package entrypoints, API handlers, shared types) |
| **Database** | PostgreSQL 16 · Prisma in `@immo/db` |
| **Migrations** | `prisma migrate dev` with descriptive name; comment non-obvious columns in migration SQL; never edit applied migrations — add a new one |
| **Domain vs persistence** | Screening/financing math lives in `@immo/domain`; Prisma queries in `@immo/db`; workers/apps import both, do not duplicate formulas |
| **PII** | Strip contact/agent fields at ingest; never expose raw PII via API (`docs/M1-PLAN.md`) |
| **Implementation hygiene** | No unused imports; timeouts on external I/O (Playwright, HTTP); narrow caught exceptions; avoid broad silent catch-and-continue |

Package layout:

```
apps/api, apps/web     stubs until M2/M4 — follow docs/ARCHITECTURE.md when implementing
packages/db            Prisma schema + client
packages/domain        screening math + vitest
workers/ingest         M1 active
workers/screening      M3
docker/                Postgres dev only (127.0.0.1:5432)
```

---

## PR checklist (product)

Use this before opening a product PR from the worktree:

- [ ] Code edits only under `sessions/<codename>/worktrees/immo/`
- [ ] `pnpm test` and `pnpm build` pass
- [ ] Doc sync map rows above satisfied for this change
- [ ] Schema changes: migration + RFC/milestone docs updated
- [ ] Domain math: golden fixture updated if expected values change
- [ ] Feature branch — no direct push to `main` unless explicitly requested

**Product PR flow:** branch from `main` in the worktree, push, open PR on `lgarciaaco/immo-investor`. Add `CONTRIBUTING.md` in the product worktree when formalizing review rules; until then, `README.md` + this doc apply.

**Hub PR flow** (scripts, sessions, this file): [CONTRIBUTING.md](../CONTRIBUTING.md) at hub root.

---

## Hub vs product

| Layer | Repo / path | Guidelines |
|-------|-------------|------------|
| Session binding, worktrees, hooks | Hub root | [AGENTS.md](../AGENTS.md) · [SESSIONS.md](../SESSIONS.md) |
| Product code + docs | `sessions/<codename>/worktrees/immo/` | This file |
| Reference clone (read-only) | `repos/immo/` | Search and cite; refresh with `./scripts/clone-repos.sh` |

Do not duplicate session/git rules here — they live in AGENTS.md and `BOUNDARIES.md`.
