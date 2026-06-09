# Scope collector procedure

1. Resolve target path and scope mode from orchestrator
2. Compute delta per [scope-and-delta.md](../../references/scope-and-delta.md)
3. Build file list with `path`, `language`, `kind` (`code`|`doc`|`config`|`test`)
4. Language: extension dispatch (`.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`)
5. Doc files: `*.md`, `docs/**`, `README*`, `CONTRIBUTING*`, `.cursor/skills/**/SKILL.md`
6. Build `doc_corpus` — full doc set for consistency review (hub: AGENTS.md, SESSIONS.md, docs/, skills)
7. Set `triggers.security` / `triggers.performance` per orchestrator rules
8. Write `scope_manifest.json` to workspace root — no findings
9. **Workflow session:** when `sessions/<codename>/workflow.json` exists and `gates.plan_user_accepted` is true, run:
   `python3 scripts/workflow-code-review-enrich-scope.py <codename> <workspace-relative-to-hub-root>`
   Adds `workflow.acceptance_criteria` from `action-plan.md` for the intent reviewer.
