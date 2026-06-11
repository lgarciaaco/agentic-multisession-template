---
name: code-reviewer
description: >-
  Multi-agent code and documentation review with auto-computed scope. Spawns
  specialist Task subagents; synthesizes unified report. Use for code review,
  audit, quality gate, docs review, or verify session work.
---

# Code reviewer

Multi-agent review. Orchestrator computes scope, spawns specialists via Task, synthesizes report.

## Target

1. `./scripts/resolve-session.sh` when session-bound
2. Product: `sessions/<codename>/worktrees/<repo>/`
3. Session metadata: `sessions/<codename>/` only
4. Ad hoc: user directory

## Scope modes

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

## Subagent isolation (mandatory)

| Role | Runner |
|------|--------|
| Code (per language), docs, test, intent, structure, security, performance | **Task subagent** — orchestrator spawns parallel |
| Scope collector | Orchestrator inline → `scope_manifest.json` |
| Synthesizer | Orchestrator inline → `report.md` + persistence |

Orchestrator must **not** write specialist `findings/*.json` inline. Violations invalidate the review run.

Workflow code loop: load this skill; enrich via `workflow-code-review-enrich-scope.py`; advance via `workflow-code-review-advance.py`.

## Pipeline

### 1. Scope collector (inline)

[agents/scope-collector.md](agents/scope-collector.md) + [rules/agents/scope-collector.md](rules/agents/scope-collector.md) → `scope_manifest.json`.

### 2. Specialists (Task, parallel)

**Model:** `claude-4.6-sonnet-medium-thinking` — pass as `model` on every specialist Task call. Extended thinking catches cross-cutting issues (data flow, intent violations, subtle security gaps) that fast models surface-read. To update the slug, edit this line and the entry in `.cursor/skills/workflow-orchestrator/SKILL.md ## Model assignments`.

Wait for all. Skip agents whose scope is empty — except Docs (always runs; falls back to repo scan when `doc_corpus` is missing).

| Agent | When | Spec |
|-------|------|------|
| Code Python | `language: python` in manifest | [agents/code-reviewer.md](agents/code-reviewer.md) |
| Code TypeScript | `language: typescript` | [agents/code-reviewer.md](agents/code-reviewer.md) |
| Docs | always | [agents/docs-reviewer.md](agents/docs-reviewer.md) |
| Test | `changeset` or `task` | [agents/test-reviewer.md](agents/test-reviewer.md) |
| Intent | session acceptance/goal or user intent | [agents/intent-reviewer.md](agents/intent-reviewer.md) |
| Structure | `triggers.structure` (code in manifest) | [agents/structure-reviewer.md](agents/structure-reviewer.md) |
| Security | `triggers.security` | [agents/security-reviewer.md](agents/security-reviewer.md) |
| Performance | `triggers.performance` | [agents/performance-reviewer.md](agents/performance-reviewer.md) |

Use Task prompts in each `agents/*.md`. Pass `workspace`. Output: `findings/<agent>.json`.

Readability stays in code agents.

### 3. Synthesizer (inline)

[agents/synthesizer.md](agents/synthesizer.md) + [rules/agents/synthesizer.md](rules/agents/synthesizer.md) → merge, dedupe, verdict, `report.md`. Persist: [references/persistence.md](references/persistence.md).

## Verdict

| Verdict | When |
|---------|------|
| FAIL | Any BLOCKER (code or security) |
| INCOMPLETE | Any REQUIRED; any open SUGGESTION/NIT in findings; unmet intent criteria |
| PASS | Clean findings (validated refusals in disposition artifact only) |

Workflow: open SUGGESTION/NIT → fixer dispositions → specialist validation ([disposition-validation.md](rules/disposition-validation.md)). `PASS_WITH_NITS` is legacy when findings are empty after validation.

Docs: REQUIRED max (no BLOCKER). [rules/documentation.md](rules/documentation.md).

## Report sections

Summary, Scope, Verdict, Code, Structure, Documentation, Tests, Intent, Security (if ran), Positive notes, Deferred to CI.

## Pre-delivery

- [ ] All spawned agents wrote findings JSON or explicit empty findings
- [ ] Dedupe; BLOCKER only from code/security
- [ ] Session: `reviews/r-NNN.json`, `progress.last_review`
- [ ] `./scripts/sync-session.sh <codename>` when bound

## Writable

`sessions/<codename>/reviews/**`, `progress.json`. Never edit worktrees from review agents.

## Rule index

| Layer | Files |
|-------|-------|
| Code | [rules/universal.md](rules/universal.md) → [rules/agents/code-reviewer.md](rules/agents/code-reviewer.md) → [languages/*.md](languages/) |
| Docs | [rules/documentation.md](rules/documentation.md) → [rules/agents/docs-reviewer.md](rules/agents/docs-reviewer.md) |
| Tests | universal → [rules/agents/test-reviewer.md](rules/agents/test-reviewer.md) |
| Structure | [rules/structure.md](rules/structure.md) → [rules/agents/structure-reviewer.md](rules/agents/structure-reviewer.md) |
| Security | [rules/security.md](rules/security.md) → [rules/agents/security-reviewer.md](rules/agents/security-reviewer.md) |
| Performance | [rules/performance.md](rules/performance.md) → [rules/agents/performance-reviewer.md](rules/agents/performance-reviewer.md) |

## Hub skills

Improve skill copy with [skill-optimizer](../skill-optimizer/SKILL.md). Human-facing report tone: [write-like-a-human](../write-like-a-human/SKILL.md).
