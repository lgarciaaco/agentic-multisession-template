# Leaks reviewer procedure

1. Spawn when `scope_manifest.triggers.leaks` is true (default on `changeset` and `task` scope)
2. Review all manifest files in delta — focus on new/changed lines for secrets, identifiers, PII, and vulnerability hints
3. Load [leaks.md](../leaks.md)
4. Systematic pass: API keys/tokens, PEM blocks, `.env` leaks, hardcoded personal/org identifiers, PII in fixtures, obvious unsafe patterns in diff
5. BLOCKER and REQUIRED per leaks.md; cite exposure scenario (public repo, log output, committed credential)
6. Write `findings/leaks.json` with `"agent": "leaks"`
