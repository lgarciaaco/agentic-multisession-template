# Plan reviewer procedure

1. Read `plan_scope_manifest.json` — brief_path, plan_path, session_mode
2. Load [plan-reviewer.md](../plan-reviewer.md) and [findings-schema.md](../../references/findings-schema.md)
3. Read `problem-brief.md` — extract SC-1…SC-n, Constraints, Out of scope
4. Read `action-plan.md` — Approach, Traceability, Tasks, Test plan, Risks
5. Read `repos.yaml` when tasks reference repo aliases
6. Map each SC-n → criteria[] with met + evidence
7. Run DoR checks on every task; emit findings with REQUIRED/SUGGESTION/NIT only
8. SUGGESTION/NIT are non-blocking but plan-author must disposition each (accepted/refused + rationale) before user gate
9. Set verdict: APPROVE | REVISE | REJECT
9. Write `<workspace>/findings/plan.json` only — never edit action-plan.md
10. Return: verdict, criteria summary, counts by severity
