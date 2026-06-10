# Code review disposition validation

When `artifacts/code-review-disposition.md` has rows, or prior review had SUGGESTION/NIT:

| Check | FAIL when → REQUIRED |
|-------|----------------------|
| Missing row | Prior SUGGESTION/NIT has no disposition row |
| Undecided | Row missing **accepted** or **refused** |
| Accepted not applied | **accepted** but worktree unchanged for that finding |
| Refused without rationale | **refused** but rationale empty |
| Invalid refusal | rationale contradicts plan/brief or ignores valid quality gap |

On validation pass: drop validated rows from `findings[]`. **refused** validated → omit from findings (stay in disposition file).

First pass: emit SUGGESTION/NIT → synthesizer **INCOMPLETE** until fixer dispositions and you validate.

## Workflow scope

When `scope_manifest.workflow.include_working_tree` is true, treat staged + unstaged changes in the target worktree as part of the changeset (no commit gate).
