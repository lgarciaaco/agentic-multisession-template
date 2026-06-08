# Intent reviewer procedure

1. Read `scope_manifest.json`, `TASKS.md`, `session.json` tasks (acceptance, files_in_scope)
2. Read git log for delta range when present
3. Map each acceptance criterion → MET | NOT MET with evidence
4. Flag scope creep: delta files outside `files_in_scope` → SUGGESTION
5. Unmet acceptance → REQUIRED finding or `criteria[].met: false`
6. Skip if no session and no user-stated intent in orchestrator prompt
7. Write `findings/intent.json` (criteria + findings)
