# Plan author procedure

1. Read `plan_scope_manifest.json` — brief_path, plan_path, prior_findings, user_feedback
2. Load [plan-author.md](../plan-author.md)
3. Read frozen `problem-brief.md`; read `repos.yaml` for valid aliases
4. On REVISE: read `findings/plan.json`
   - Apply every **REQUIRED** finding to the plan (or document in **Revision notes**)
   - For each **SUGGESTION** and **NIT**: decide **accepted** or **refused**; never skip
   - **accepted**: edit plan to address finding; note in disposition row
   - **refused**: keep plan unchanged for that item; cite brief constraint, out-of-scope, or defer to task id in rationale
   - Write all rows to **Reviewer disposition** table
5. If `artifacts/plan-feedback.md` exists, read and incorporate
6. Write `artifacts/action-plan.md` per template — increment Version on revise
7. Do not edit worktrees, session.json, or brief
8. Return: version, task count, SC traceability summary, disposition counts (accepted/refused SUGGESTION+NIT)
