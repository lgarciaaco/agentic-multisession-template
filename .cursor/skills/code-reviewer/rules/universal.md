# Universal rules

Skip unless requested: `node_modules/`, `.venv/`, `venv/`, `dist/`, `build/`, `coverage/`, `__pycache__/`, `*.min.js`, `.git/`, lockfiles, generated stubs.

## Design

- Flag functions >50 lines, god objects, speculative future code, unchecked public API changes
- Flag nesting >4 levels; light duplication hint only — defer deep duplication/layout/dead-code to structure agent

## Correctness

- BLOCKER: mishandled empty/null/boundary inputs on new paths
- Flag silent success on error paths, off-by-one, check-then-act without sync
- Flag precision loss on money/ID fields without explicit handling

## Security

- BLOCKER: string-built SQL/shell/LDAP/OS commands — use safe APIs
- BLOCKER: hardcoded credentials, keys, tokens, connection strings
- BLOCKER: user input to filesystem, process spawn, `eval`, redirects without validation
- Flag missing auth on new endpoints, `*` CORS/CSP, secrets/PII in logs, `verify=False` on prod HTTP

## Async, resources, errors

- Flag unsynchronized shared mutable state, fire-and-forget async, I/O without timeout, unbounded queues
- Flag resources not released on all paths, unbounded in-memory growth
- REQUIRED: empty catch blocks; flag catch-all where specific fits; flag control-flow via exceptions; flag rethrow without cause

## Performance

- Flag N+1 queries, unbounded fetches, sync blocking on concurrent paths, hot-loop string concat

## Tests (light pass — test agent owns deep review on changeset/task)

- Flag obvious missing tests on new public behavior in touched files
- Defer coverage/acceptance checks to test reviewer agent

## Dependencies (changeset)

- Flag unpinned new deps or duplicate capability; cite audit tool output for CVEs — do not invent

## Depth

- `full`: security + design on prioritized files; correctness on reviewed source
- `changeset`/`task`: deep on hunks; tests + security on touched files and callers
