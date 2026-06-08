# Findings JSON schema

Every specialist agent writes one file under `<workspace>/findings/`.

## Envelope

```json
{
  "agent": "code-python",
  "findings": [
    {
      "severity": "BLOCKER",
      "file": "scripts/foo.py",
      "line": 42,
      "issue": "short description",
      "fix": "concrete suggestion",
      "confidence": "HIGH"
    }
  ]
}
```

## Fields

| Field | Required | Values |
|-------|----------|--------|
| `agent` | yes | `scope-collector`, `code-python`, `code-typescript`, `docs`, `intent`, `tests`, `security`, `performance` |
| `findings[].severity` | yes | `BLOCKER`, `REQUIRED`, `SUGGESTION`, `NIT` |
| `findings[].file` | yes* | repo-relative path; `intent` may use criterion id in `file` |
| `findings[].line` | no | integer when applicable |
| `findings[].issue` | yes | |
| `findings[].fix` | no | |
| `findings[].confidence` | no | `HIGH`, `MEDIUM`, `LOW` |

## Intent agent variant

```json
{
  "agent": "intent",
  "criteria": [
    {"id": "acceptance-1", "criterion": "text", "met": false, "evidence": "..."}
  ],
  "findings": []
}
```

Unmet criteria → add `REQUIRED` finding or populate `criteria` with `met: false`; synthesizer treats `met: false` as INCOMPLETE input.

## scope_manifest.json

```json
{
  "review_id": "review-20260608-120000",
  "scope": "full",
  "target": "/path/to/repo",
  "range": null,
  "delta_strategy": "full",
  "files": [
    {"path": "scripts/foo.py", "language": "python", "kind": "code"},
    {"path": "AGENTS.md", "language": null, "kind": "doc"}
  ],
  "doc_corpus": ["AGENTS.md", "SESSIONS.md", "docs/REPOS.md"],
  "triggers": {"security": true, "performance": false}
}
```

`triggers` set by orchestrator (see SKILL.md).
