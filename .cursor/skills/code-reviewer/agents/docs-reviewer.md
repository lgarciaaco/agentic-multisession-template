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
Read scope_manifest.json. Review entire doc_corpus for consistency, duplication, coherence — not delta-only.
Cross-check commands and paths against scripts/, .cursor/, sessions/ layout.

Load .cursor/skills/code-reviewer/rules/documentation.md and rules/agents/docs-reviewer.md.
Doc findings default to REQUIRED (never BLOCKER).

Write <workspace_path>/findings/docs.json per references/findings-schema.md.
Return: file path + counts by severity.
```
