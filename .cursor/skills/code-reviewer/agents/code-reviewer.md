# Agent: code reviewer (per language)

**Spawn:** Task parallel, one per language in manifest. **Output:** `findings/code-python.json` or `findings/code-typescript.json`

## Load

1. [rules/universal.md](../rules/universal.md)
2. [rules/agents/code-reviewer.md](../rules/agents/code-reviewer.md)
3. [languages/python.md](../languages/python.md) OR [languages/typescript.md](../languages/typescript.md)

## Task prompt template

```text
Code review agent (<language>).

Workspace: <workspace_path>
Read scope_manifest.json. Review only files where language=<language> and kind=code.

Load skill rules from .cursor/skills/code-reviewer/:
- rules/universal.md
- rules/agents/code-reviewer.md
- languages/<language>.md

Write findings to <workspace_path>/findings/code-<language>.json per references/findings-schema.md.
Return only: file path written + finding counts by severity.
```
