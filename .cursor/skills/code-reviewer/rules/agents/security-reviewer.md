# Security reviewer procedure (optional)

1. Spawn only when `scope_manifest.triggers.security` is true
2. Review manifest files under auth/api/middleware/security paths + all code in changeset when small
3. Load [security.md](../security.md) + language files for langs in scope
4. Systematic pass: injection, authz, secrets, deserialization, path traversal
5. BLOCKER and REQUIRED per security.md; cite attack scenario
6. Write `findings/security.json`
