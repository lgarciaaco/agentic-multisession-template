---
name: code-reviewer
description: >-
  Multi-agent code and documentation review with auto-computed scope. Orchestrates
  parallel specialists (code per language, docs, tests, intent, optional security)
  and synthesizes a unified report. Use for code review, audit codebase, check whole
  repo, review changes, quality gate, documentation review, or verify session work.
---

# Code reviewer (orchestrator)

Multi-agent review. Not PR workflow. Orchestrator computes scope, spawns specialists via Task, synthesizes report.

## Target

1. `./scripts/resolve-session.sh` → session-bound or ad hoc
2. Product: `sessions/<codename>/worktrees/<repo>/`
3. Hub: hub root + `sessions/<codename>/` metadata
4. Ad hoc: user directory

## Scope

| Mode | Triggers |
|------|----------|
| `full` | whole repo, audit |
| `changeset` | my changes, quality gate |
| `files` | named paths |
| `task` | verify task `<id>` |

Default: audit → `full`; bound session → `changeset`. Delta: [references/scope-and-delta.md](references/scope-and-delta.md).

## Workspace

| Context | Path |
|---------|------|
| Session | `sessions/<codename>/reviews/workspace/<review-id>/` |
| Ad hoc | `~/.cursor/reviews/workspace/<review-id>/` |

`review-id` = `review-YYYYMMDD-HHMMSS`. Layout: [references/workspace.md](references/workspace.md).

```bash
mkdir -p "<workspace>/findings"
```

## Pipeline

### 1. Scope collector (inline)

Follow [agents/scope-collector.md](agents/scope-collector.md) + [rules/agents/scope-collector.md](rules/agents/scope-collector.md).

Write `<workspace>/scope_manifest.json` per [references/findings-schema.md](references/findings-schema.md).

### 2. Spawn specialists (Task, parallel)

Wait for all. Skip agents with nothing to do.

| Agent | Spawn when | Spec |
|-------|------------|------|
| Code Python | manifest has `language: python` | [agents/code-reviewer.md](agents/code-reviewer.md) |
| Code TypeScript | manifest has `language: typescript` | [agents/code-reviewer.md](agents/code-reviewer.md) |
| Docs | always (corpus in manifest) | [agents/docs-reviewer.md](agents/docs-reviewer.md) |
| Test | scope is `changeset` or `task` | [agents/test-reviewer.md](agents/test-reviewer.md) |
| Intent | session + acceptance/goal, or user intent | [agents/intent-reviewer.md](agents/intent-reviewer.md) |
| Security | `triggers.security` | [agents/security-reviewer.md](agents/security-reviewer.md) |
| Performance | `triggers.performance` | [agents/performance-reviewer.md](agents/performance-reviewer.md) |

Use Task prompt templates in each `agents/*.md`. Pass `workspace` path. Each agent writes `findings/<agent>.json`.

**Readability** stays in code agents (no separate agent).

### 3. Synthesizer (inline)

Follow [agents/synthesizer.md](agents/synthesizer.md) + [rules/agents/synthesizer.md](rules/agents/synthesizer.md).

Merge, dedupe, verdict, write `report.md`. Persist: [references/persistence.md](references/persistence.md).

## Verdict

| Verdict | When |
|---------|------|
| FAIL | Any BLOCKER (code or security agents) |
| INCOMPLETE | Any REQUIRED (docs, tests, intent, code) without BLOCKER |
| PASS_WITH_NITS | Only SUGGESTION/NIT |
| PASS | Clean |

Docs agent: REQUIRED max (no BLOCKER). See [rules/documentation.md](rules/documentation.md).

## Report template

```markdown
# Code Review — [scope] — [target]

## Summary
## Scope
review-id, workspace, files by kind/lang, delta

## Verdict: PASS | PASS_WITH_NITS | INCOMPLETE | FAIL

## Code
[blocker/required/suggestion by language]

## Documentation
[corpus findings]

## Tests
[if test agent ran]

## Intent
[if intent agent ran]

## Security
[if security agent ran]

## Positive notes
## Deferred to CI
```

## Pre-delivery

- [ ] All spawned agents wrote findings JSON or explicit empty findings
- [ ] Dedupe applied; BLOCKER only from code/security
- [ ] Session: `reviews/r-NNN.json`, `progress.last_review`, optional checkpoint
- [ ] `./scripts/sync-session.sh <codename>` when session-bound

## Writable

`sessions/<codename>/`: `reviews/workspace/`, `reviews/r-*.json`, `checkpoints.json`, `progress.json`. Ad hoc: `~/.cursor/reviews/**`. Never edit worktrees.

## Rule index

| Layer | Files |
|-------|-------|
| Code | [rules/universal.md](rules/universal.md) → [rules/agents/code-reviewer.md](rules/agents/code-reviewer.md) → [languages/*.md](languages/) |
| Docs | [rules/documentation.md](rules/documentation.md) → [rules/agents/docs-reviewer.md](rules/agents/docs-reviewer.md) → [languages/docs-*.md](languages/) |
| Tests | universal (tests) → [rules/agents/test-reviewer.md](rules/agents/test-reviewer.md) |
| Security | [rules/security.md](rules/security.md) → [rules/agents/security-reviewer.md](rules/agents/security-reviewer.md) |
| Performance | [rules/performance.md](rules/performance.md) → [rules/agents/performance-reviewer.md](rules/agents/performance-reviewer.md) |
