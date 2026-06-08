# Synthesizer procedure (orchestrator runs inline)

1. Load all `findings/*.json` from workspace
2. Dedupe: same `file` + `line` + similar `issue` → keep highest severity
3. Resolve conflicts: security BLOCKER beats performance SUGGESTION; prefer specific agent over code-agent duplicate
4. Intent: any `criteria[].met: false` → contributes to INCOMPLETE
5. Verdict:
   - **FAIL**: any BLOCKER (code or security agents only)
   - **INCOMPLETE**: any REQUIRED (docs, tests, intent, code) without BLOCKER
   - **PASS_WITH_NITS**: only SUGGESTION/NIT
   - **PASS**: clean
6. Write `report.md` to workspace; copy summary to session `reviews/r-NNN.json`
7. Update `progress.last_review`; `./scripts/sync-session.sh <codename>` if session-bound
8. Optional: remove workspace dir after successful persist
