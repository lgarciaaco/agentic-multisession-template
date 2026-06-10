# Agent: structure reviewer

**Spawn:** Task parallel when `triggers.structure`. **Output:** `findings/structure.json`

Covers code duplication, project layout, redundant new code, and dead code after removals. Docs duplication is docs agent only.

## Load

1. [rules/structure.md](../rules/structure.md)
2. [rules/agents/structure-reviewer.md](../rules/agents/structure-reviewer.md)

## Task prompt template

```text
Structure review agent.

Workspace: <workspace_path>
Hub root: <hub_root>
Read scope_manifest.json. triggers.structure must be true.

Load .cursor/skills/code-reviewer/rules/structure.md and rules/agents/structure-reviewer.md.

Review manifest code files (and scripts/config in delta):
- Duplication: new logic that repeats existing repo code — cite existing path
- Layout: paths vs docs/PROJECT.md ## Layout or repo conventions
- Redundant add: new capability that already exists elsewhere
- Dead code: orphans after feature removal (imports, tests, docs, scripts, skills)

Search (rg/grep) before REQUIRED duplication findings.
Never BLOCKER — REQUIRED, SUGGESTION, NIT only.

Write <workspace_path>/findings/structure.json (agent: structure).
Return: file path + counts by severity.
```
