# Structure rules (duplication, layout, dead code)

Deep pass for codebase shape. Code agents apply light duplication hints only ([universal.md](universal.md)); docs agent covers **documentation** duplication only ([documentation.md](documentation.md)).

No BLOCKER severity — use REQUIRED, SUGGESTION, NIT.

## Duplication (code)

- REQUIRED: new module or function substantially repeats existing logic in the same repo (same algorithm, renamed variables, copy-paste with edits)
- REQUIRED: parallel helpers for the same concern (two parsers, two validators, two session binders) without clear boundary
- SUGGESTION: near-duplicate blocks >15 lines across files in delta; recommend extract or reuse
- NIT: cosmetic similarity with different purpose

Search before flagging REQUIRED: `rg`/grep for distinctive strings, function names, or error messages from the new code.

## Redundant introduction

When delta **adds** code:

- REQUIRED if an existing export, script, or skill already provides the same capability (extend instead)
- REQUIRED if new file duplicates an existing registry entry pattern (second clone script, second status checker) without brief/plan justification

Cite the existing path in `fix`.

## Project layout

Read `docs/PROJECT.md` **## Layout** when present (hub: `docs/PROJECT.md` at hub root; product: hub-relative path from `repos.yaml` `guidelines.project`).

- REQUIRED: new code in path that contradicts documented layout (product under wrong package, hub script outside `scripts/`, skill outside `.cursor/skills/`)
- REQUIRED: new top-level directory without layout doc update when PROJECT.md defines top-level map
- SUGGESTION: file name or folder breaks repo conventions (mixed case, domain logic in `utils/` that belongs in `lib/`)

Hub template defaults when no PROJECT.md layout:

| Area | Expected |
|------|----------|
| Session scripts | `scripts/` |
| Hooks, rules, skills | `.cursor/` |
| Hub docs | `docs/`, `AGENTS.md`, `SESSIONS.md` |
| Product code | worktree root per repo — not `repos/` |

## Dead code and removal hygiene

When delta **removes** a feature or renames entrypoints:

- REQUIRED: orphaned files still referenced nowhere (scripts, rules, tests, docs) after removal
- REQUIRED: stale imports, CLI commands, or skill triggers pointing at deleted paths
- REQUIRED: tests exclusively covering removed behavior left in tree without `@deprecated` migration path
- SUGGESTION: unused exports or functions with zero references in repo (confirm not public API)

When delta **only adds**: still flag dead paths if new code supersedes old and old was not deleted in same changeset.

## Scope

- Review manifest code files + config/scripts touched in delta
- Cross-repo: one worktree at a time; do not compare across `sessions/*/worktrees/*` aliases
- Do not flag generated, vendor, or lockfile paths per universal skip list

## Severity cap

Structure agent never emits BLOCKER. Synthesizer maps REQUIRED → INCOMPLETE.
