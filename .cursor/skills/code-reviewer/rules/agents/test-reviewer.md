# Test reviewer procedure

1. Run only for `changeset` or `task` scope (orchestrator skips otherwise)
2. Read `scope_manifest.json` — code files in delta + test files (`kind: test` or `test_*.py`, `*.test.ts`, `*.spec.ts`)
3. Load universal.md tests section only (or full universal if short)
4. Flag new/changed behavior without test changes in delta
5. Flag tests that only assert no-throw; weakened/removed tests without reason
6. Cross-check acceptance criteria mentioning tests
7. Write `findings/tests.json`
