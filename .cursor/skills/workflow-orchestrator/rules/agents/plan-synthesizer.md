# Plan synthesizer procedure (conductor runs inline)

1. Load `<workspace>/findings/plan.json`
2. Dedupe findings: same issue text → keep highest severity
3. Any `criteria[].met: false` → contributes to REVISE (unless REJECT already set)
4. Verdict:
   - **REJECT**: agent set REJECT, or brief fundamentally misread
   - **REVISE**: any REQUIRED finding; any unmet criterion; **any SUGGESTION or NIT** (open dispositions or first-pass quality findings)
   - **APPROVE**: all criteria met; no REQUIRED; **no SUGGESTION or NIT in findings** (validated refusals remain in plan disposition table only)
5. Write `<workspace>/report.md` — summary, criteria table, findings by severity, verdict
6. Persist `artifacts/plan-review/pr-NNN.json` + `pr-NNN-report.md`
7. Update `workflow.loops.plan.last_verdict` and iteration in `workflow.json`
8. On APPROVE: conductor may set **Status** line in `action-plan.md` header to `reviewer_approved` only — no other plan body edits

## pr-NNN.json shape

```json
{
  "id": "pr-001",
  "at": "<iso>",
  "workflow_id": "wf-20260609-120000",
  "verdict": "REVISE",
  "findings_count": {"required": 2, "suggestion": 1, "nit": 0}
}
```
