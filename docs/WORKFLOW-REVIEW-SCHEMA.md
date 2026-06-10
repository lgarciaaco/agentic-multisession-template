# Workflow review findings schema

Shared envelope and severity vocabulary for **plan review** and **code review** specialist outputs. Skill-specific rules (plan `verdict`, code `scope_manifest`, intent criteria) stay in:

- [code-reviewer references/findings-schema.md](../.cursor/skills/code-reviewer/references/findings-schema.md)
- [workflow-orchestrator references/findings-schema.md](../.cursor/skills/workflow-orchestrator/references/findings-schema.md)

---

## Envelope

Every specialist agent writes one JSON file under `<workspace>/findings/` (e.g. `findings/plan.json`, `findings/code-python.json`).

```json
{
  "agent": "<agent-id>",
  "findings": [
    {
      "severity": "REQUIRED",
      "file": "path/relative/to/repo-or-artifact",
      "line": 42,
      "issue": "short description",
      "fix": "concrete suggestion",
      "confidence": "HIGH"
    }
  ]
}
```

Optional top-level fields (agent-specific): `criteria[]`, `verdict` (plan reviewer only). See skill references for those extensions.

---

## Finding fields

| Field | Required | Values |
|-------|----------|--------|
| `agent` | yes | Agent id — e.g. `plan`, `code-python`, `docs`, `intent`, `tests`, `security` |
| `findings[].severity` | yes | See severity table below |
| `findings[].file` | yes* | Repo-relative path or artifact ref (`artifacts/action-plan.md`); intent may use criterion id |
| `findings[].line` | no | Integer when applicable |
| `findings[].issue` | yes | |
| `findings[].fix` | no | Actionable fix or suggestion |
| `findings[].confidence` | no | `HIGH`, `MEDIUM`, `LOW` |

---

## Severity vocabulary

| Severity | Plan review | Code review | Meaning |
|----------|-------------|-------------|---------|
| `BLOCKER` | **never** | yes | Critical defect; blocks merge / PASS |
| `REQUIRED` | yes | yes | Must fix before APPROVE / PASS |
| `SUGGESTION` | yes | yes | Author/fixer dispositions (accept/refuse + rationale) |
| `NIT` | yes | yes | Style/minor; same disposition loop as SUGGESTION |

**Plan loop:** synthesizer **REVISE** while any REQUIRED, unmet criterion, or open SUGGESTION/NIT remains. **APPROVE** when criteria met and `findings[]` has no REQUIRED, SUGGESTION, or NIT.

**Code loop:** synthesizer **INCOMPLETE** while any BLOCKER or REQUIRED remains; SUGGESTION/NIT follow fixer disposition → specialist re-validation until **PASS**.

---

## Intent agent variant (code review)

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

---

## Workspace layout

| Loop | Workspace dir | Primary findings file |
|------|---------------|----------------------|
| Plan | `sessions/<codename>/reviews/workspace/wf-<timestamp>/` | `findings/plan.json` |
| Code | `sessions/<codename>/reviews/workspace/review-<timestamp>/` | `findings/*.json` per specialist |

Persisted summaries: `artifacts/plan-review/pr-NNN.json`, `reviews/r-NNN.json`.
