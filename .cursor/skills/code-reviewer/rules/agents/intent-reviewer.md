# Intent reviewer procedure

1. Read `scope_manifest.json`, `TASKS.md`, `session.json` tasks (acceptance, files_in_scope)
2. **Workflow sessions:** when `scope_manifest.json` has `workflow.acceptance_criteria`, map each entry's `acceptance` field (from `action-plan.md` ## Tasks) → criterion. Prefer this over TASKS.md for the same task `id`. If `workflow` block is missing but `workflow.json` exists under the session, read `artifacts/action-plan.md` ## Tasks table directly.
3. Read git log for delta range when present
4. Map each acceptance criterion → MET | NOT MET with evidence
5. Flag scope creep: delta files outside `files_in_scope` → SUGGESTION
6. Unmet acceptance → REQUIRED finding or `criteria[].met: false`
7. Skip if no session and no user-stated intent in orchestrator prompt
8. Write `findings/intent.json` (criteria + findings)
