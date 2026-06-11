# Git commit

Create conventional commits with branch safety and staging verification.

## Triggers

Use when user says "commit", "create commit", "git commit", "save changes", or "commit changes".

## Procedure

1. **Branch safety** — run `git branch --show-current`. If on main/master, suggest creating a feature branch first.

2. **Staging check** — run `git diff --cached --stat`. If nothing staged, show unstaged changes (`git status -s`) and ask what to stage.

3. **Generate commit message** — conventional-commit format:

```
<type>(<scope>): <description>

<body explaining what and why>
```

| Field | Rules |
|-------|-------|
| `type` | `feat`, `fix`, `build`, `chore`, `ci`, `docs`, `style`, `refactor`, `perf`, `test` |
| `scope` | Short module or area name (optional but preferred) |
| `description` | Imperative, lowercase, no period, ≤72 chars |
| `body` | What changed and why; wrap at 72 chars; optional for trivial commits |

4. **Present and confirm** — show the message, ask user to confirm or revise. Skip this step when loaded from workflow `pr_creation` or `ci_observe` phase (autonomous — commit directly).

5. **Commit** — execute with HEREDOC:

```bash
git commit -m "$(cat <<'EOF'
<message>
EOF
)"
```

6. **Verify** — run `git status` after commit to confirm clean state.

## Rules

- Never commit on main/master without explicit user approval
- Never skip staging verification
- Never add AI attribution in commit messages
- Write as a human developer — informal, direct
- One logical change per commit when possible
