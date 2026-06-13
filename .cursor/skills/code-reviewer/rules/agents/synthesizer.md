# Synthesizer procedure (orchestrator runs inline)

1. Load all `findings/*.json` from workspace
2. Dedupe: same `file` + `line` + similar `issue` → keep highest severity
3. Resolve conflicts: leaks, security, or infra-yaml BLOCKER beats performance SUGGESTION; prefer specific agent over code-agent duplicate
4. Intent: any `criteria[].met: false` → contributes to INCOMPLETE
5. Open **SUGGESTION** or **NIT** in merged findings → **INCOMPLETE** (fixer dispositions; validate on next pass). See [disposition-validation.md](../disposition-validation.md).
6. Verdict:
   - **FAIL**: any BLOCKER (code, leaks, security, or infra-yaml agents)
   - **INCOMPLETE**: any REQUIRED; any SUGGESTION/NIT in findings; unmet intent criteria
   - **PASS**: clean findings (validated refusals in `artifacts/code-review-disposition.md` only)
7. Write `report.md` to workspace; copy summary to session `reviews/r-NNN.json`
8. Update `progress.last_review`; `./scripts/sync-session.sh <codename>` if session-bound
9. Optional: remove workspace dir after successful persist
