# Code fixer (parent agent — not Task)

**Invoke:** conductor during `code_review_loop` after **INCOMPLETE** / recoverable **FAIL**.

Load [code-fixer.md](../rules/code-fixer.md).

## Task prompt (self — parent agent)

```text
Code fixer — autonomous workflow loop.

Session: <codename>
Task slice: <task_id>
Read reviews/r-NNN-report.md (latest).
Read artifacts/code-review-disposition.md — append/update rows for this review.

Fix every REQUIRED finding in sessions/<codename>/worktrees/**.
For each SUGGESTION/NIT: accepted (apply) or refused (rationale) in disposition table.
Do not ask user to commit. Do not pause for PR approval.

When done: conductor re-runs code-reviewer skill (new review-* workspace).
Return: files changed, disposition counts, remaining REQUIRED count (expect 0).
```
