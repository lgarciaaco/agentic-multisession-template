# Plan review findings schema

Specialist agents write one file under `<workspace>/findings/`. Plan review uses the same severity vocabulary as code-reviewer except **no BLOCKER** (no code under review).

## plan.json envelope

```json
{
  "agent": "plan",
  "criteria": [
    {
      "id": "SC-1",
      "criterion": "text from problem-brief.md Success criteria",
      "met": true,
      "evidence": "t1, t2 in artifacts/action-plan.md Tasks"
    }
  ],
  "findings": [
    {
      "severity": "REQUIRED",
      "file": "artifacts/action-plan.md",
      "line": null,
      "issue": "short description",
      "fix": "concrete suggestion for plan-author",
      "confidence": "HIGH"
    }
  ],
  "verdict": "REVISE"
}
```

## Fields

| Field | Required | Values |
|-------|----------|--------|
| `agent` | yes | `plan` |
| `criteria[].id` | yes | `SC-1` … matching brief success criteria order |
| `criteria[].criterion` | yes | verbatim or paraphrase from brief |
| `criteria[].met` | yes | boolean |
| `criteria[].evidence` | yes when `met: true` | plan task IDs or section refs |
| `findings[].severity` | yes | `REQUIRED`, `SUGGESTION`, `NIT` — never `BLOCKER` |
| `findings[].file` | yes | `artifacts/action-plan.md`, `artifacts/problem-brief.md`, or section ref |
| `findings[].issue` | yes | |
| `findings[].fix` | no | actionable for plan-author on REVISE |
| `verdict` | yes | `APPROVE`, `REVISE`, `REJECT` |

## Verdict rules (plan synthesizer)

| Verdict | When |
|---------|------|
| `APPROVE` | All `criteria[].met: true`; no REQUIRED findings |
| `REVISE` | Any REQUIRED finding; or any `criteria[].met: false` where brief is still valid |
| `REJECT` | Plan reveals fundamental misunderstanding of brief — user must `reopen brief` |

## plan_scope_manifest.json (plan loop workspace)

```json
{
  "workflow_id": "wf-20260609-120000",
  "phase": "plan_review",
  "codename": "alpha",
  "brief_path": "sessions/alpha/artifacts/problem-brief.md",
  "plan_path": "sessions/alpha/artifacts/action-plan.md",
  "session_mode": "hub",
  "prior_findings": "findings/plan.json",
  "user_feedback": "artifacts/plan-feedback.md"
}
```

Written by `write_plan_scope_manifest()` in `scripts/lib/workflow_plan.py`. `prior_findings` and `user_feedback` optional on first iteration. Plan reviewer reads `repos.yaml` directly — repo aliases are not duplicated in the manifest.

## Persistence (after synthesize)

- `sessions/<codename>/artifacts/plan-review/pr-NNN.json` — summary
- `sessions/<codename>/artifacts/plan-review/pr-NNN-report.md` — human report
- Workspace under `sessions/<codename>/reviews/workspace/wf-<id>/` may be pruned after persist
