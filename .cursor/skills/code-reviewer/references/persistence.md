# Session persistence

Implementing agents do not write diffs. Reviewer writes review artifacts.

| File | Writer | Role |
|------|--------|------|
| `session.json` | implementer | `tasks[].acceptance`, `files_in_scope` |
| `TASKS.md` | implementer | goal, notes |
| `checkpoints.json` | reviewer | baseline SHAs (auto on first review) |
| `reviews/r-NNN.json` | reviewer | append-only history |
| `progress.json` | reviewer | `last_review` pointer |

## checkpoints.json (auto if missing)

```json
{"worktrees":{"project":{"path":"sessions/<codename>/worktrees/project","baseline_sha":"<sha>","baseline_ref":"main","captured_at":"<iso>"}}}
```

Capture: `git merge-base <base_branch> HEAD || git rev-parse HEAD` in worktree.

## reviews/r-NNN.json

```json
{"id":"r-001","at":"<iso>","scope":"full|changeset","target":"<path>","range":"abc..def|null","head_sha":"<sha>","delta_strategy":"<name>","verdict":"FAIL","findings_count":{"blocker":0,"required":0,"suggestion":0,"nit":0},"intent":{"task":"<id>","acceptance_met":false,"notes":""}}
```

## progress.json

```json
{"last_review":{"id":"r-001","at":"<iso>","verdict":"FAIL","scope":"full","blockers":0}}
```

## Optional task fields

`acceptance`: string[] — intent pass. `files_in_scope`: string[] — flag out-of-scope delta files as SUGGESTION.

## Writable

`sessions/<codename>/` only: `checkpoints.json`, `reviews/`, `progress.json`. Then `./scripts/sync-session.sh <codename>`.
