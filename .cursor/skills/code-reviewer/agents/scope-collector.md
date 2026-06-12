# Agent: scope collector

**Runs:** orchestrator inline (step 1). **Output:** `<workspace>/scope_manifest.json`

## Load

- [rules/agents/scope-collector.md](../rules/agents/scope-collector.md)
- [references/scope-and-delta.md](../references/scope-and-delta.md)
- [references/findings-schema.md](../references/findings-schema.md) (manifest shape)

## Triggers (set in manifest)

`triggers.security` = true when any:

- user prompt mentions security, audit, OWASP
- `full` scope on hub or manifest paths match `auth|api|middleware|security|hooks|scripts/lib`
- `changeset` touches those paths

`triggers.performance` = true when any:

- user prompt mentions performance, slow, N+1
- manifest has `api|db|workers|handlers` paths AND code file count > 20

Default both false for small hub-only audits unless security trigger matches.

`triggers.structure` = true when manifest includes any file with `kind: code`.

`triggers.infra` = true when any:

- user prompt mentions Ansible, GitHub Actions, GHA, deploy pipeline, or infrastructure
- manifest path matches `deploy/**`, `.github/workflows/**`, or `**/ansible/**` (any extension, including `.yml`, `.yaml`, `.sh` under those trees)

Classify matching paths as `kind: config` (see rules/agents/scope-collector.md step 8).
