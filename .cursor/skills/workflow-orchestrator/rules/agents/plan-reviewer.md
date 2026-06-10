# Plan reviewer procedure

1. Read `plan_scope_manifest.json` — brief_path, plan_path, prior_findings, session_mode
2. Load [plan-reviewer.md](../plan-reviewer.md) and [findings-schema.md](../../references/findings-schema.md)
3. Read `problem-brief.md` — extract SC-1…SC-n, Constraints, Out of scope
4. Read `action-plan.md` — Approach, Traceability, Tasks, Test plan, Risks, **Reviewer disposition**
5. Read `repos.yaml` when tasks reference repo aliases
6. If `prior_findings` set: read prior `findings/plan.json` for open SUGGESTION/NIT to validate against disposition table
7. Map each SC-n → criteria[] with met + evidence
8. Run DoR checks on every task; emit REQUIRED for gaps
9. **Disposition pass** (when disposition table exists or prior pass had SUGGESTION/NIT):
   - Validate every row: accepted → verify in plan; refused → validate rationale
   - Invalid/missing → REQUIRED finding
   - Validated items → omit from `findings[]` (do not re-emit as SUGGESTION/NIT)
10. **First pass** (no validated dispositions yet): emit SUGGESTION/NIT for non-blocking quality gaps
11. Set verdict: APPROVE only when criteria met, no REQUIRED, **no SUGGESTION/NIT left in findings[]**
12. Write `<workspace>/findings/plan.json` only — never edit action-plan.md
13. Return: verdict, criteria summary, counts by severity, disposition validated count
