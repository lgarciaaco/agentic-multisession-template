# Agent: docs reviewer

**Spawn:** Task parallel. **Output:** `findings/docs.json`

## Load

1. [rules/documentation.md](../rules/documentation.md)
2. [rules/agents/docs-reviewer.md](../rules/agents/docs-reviewer.md)
3. [languages/docs-python.md](../languages/docs-python.md) / [languages/docs-typescript.md](../languages/docs-typescript.md) if lang in manifest

## Task prompt template

```text
Documentation review agent.

Workspace: <workspace_path>
Read scope_manifest.json.

Step 1 — Corpus: use doc_corpus from manifest. If doc_corpus is empty or missing, scan the repo root
and docs/ directory for CURRENT.md, CHANGELOG.md, ROADMAP.md, docs/**/*.md and treat those as the corpus.

Step 2 — Staleness (changeset mode): if scope_mode is "changeset" and code implements features or tasks,
check whether project tracking docs (CURRENT.md, milestone plan docs) reflect the delivered work.
Flag stale status rows, outdated task markers, wrong session/branch references, missing CHANGELOG entries.
Apply rules/documentation.md § Staleness.

Step 3 — Consistency: review the corpus for accuracy, duplication, and coherence.
Cross-check commands and paths against scripts/, .cursor/, sessions/ layout.

Load .cursor/skills/code-reviewer/rules/documentation.md and rules/agents/docs-reviewer.md.
Doc findings default to REQUIRED (never BLOCKER).

Write <workspace_path>/findings/docs.json per references/findings-schema.md.
Return: file path + counts by severity.
```
