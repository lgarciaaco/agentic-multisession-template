---
name: code-reviewer
description: >-
  Language-aware code quality review with auto-computed scope (full repo, changeset,
  files, or session task). Verifies Python and TypeScript code against universal and
  language-specific rules. Use for code review, audit codebase, check whole repo,
  review changes, quality gate, or verify session task work.
---

# Code reviewer

Quality review over a computed scope. Not PR workflow. Git delta is auto-derived.

## Target

1. `./scripts/resolve-session.sh` if session-bound; else path from prompt
2. Product: `sessions/<codename>/worktrees/<repo>/`
3. Hub (`mode: hub`): hub root + `sessions/<codename>/` metadata
4. Ad hoc: user directory (must exist)

## Scope

| Mode | Triggers | Set |
|------|----------|-----|
| `full` | whole repo, audit | Source under target ([ignores](references/scope-and-delta.md)) |
| `changeset` | my changes, quality gate | Auto git delta |
| `files` | named paths | Those paths only |
| `task` | verify task `<id>` | Task worktree + delta |

Default: audit → `full`; bound session → `changeset`; named paths → `files`; named task → `task`.

Delta order: [references/scope-and-delta.md](references/scope-and-delta.md).

## Rules

1. [rules/universal.md](rules/universal.md) — always
2. `.py` → [languages/python.md](languages/python.md)
3. `.ts|.tsx|.js|.jsx|.mjs|.cjs` → [languages/typescript.md](languages/typescript.md)
4. Framework subsections: path heuristics in language files only

## Pipeline

1. Compute scope — files + optional `base..head`
2. `full`: prioritize entrypoints, auth, API, config, `src/`, `tests/`; skip vendor/generated
3. Intent (best-effort): `TASKS.md`, `tasks[].acceptance`, git log in delta, prompt
4. Review changed hunks + context (imports, callers, paired tests) against loaded rules
5. Intent pass: acceptance vs delta/code
6. Verdict + output (template below)
7. Session-bound: persist per [references/persistence.md](references/persistence.md); `./scripts/sync-session.sh <codename>`

## Severity and verdict

| Severity | Verdict trigger |
|----------|-----------------|
| BLOCKER — security, correctness, broken acceptance | FAIL if any |
| REQUIRED — likely bug, missing guard | INCOMPLETE if acceptance thin or tests missing |
| SUGGESTION / NIT | PASS_WITH_NITS if only these remain |
| (none) | PASS |

`BLOCKER:` / `REQUIRED:` prefixes in rule files map directly.

## Output

```markdown
# Code Review — [scope] — [target]

## Summary
## Scope
Mode, target, files (Py/TS counts), delta or full tree

## Verdict: PASS | PASS_WITH_NITS | INCOMPLETE | FAIL

## Blockers
[severity] file:line — issue — fix

## Intent alignment
[criterion] — MET | NOT MET

## Findings
## Test / tooling gaps
## Positive notes
## Deferred to CI
```

## Pre-delivery checks

- BLOCKER/REQUIRED cite `file:line` or acceptance id
- Stay inside computed scope; language rules match extensions only
- No style BLOCKERs when repo has linter/formatter
- Session: write `reviews/r-NNN.json`, `checkpoints.json` if missing, `progress.last_review`

## Writable (session only)

`sessions/<codename>/`: `checkpoints.json`, `reviews/`, `progress.json`. Never edit worktree product code.
