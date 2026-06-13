# Security rules (deep pass)

For optional security agent. Code agents still apply light security checks from [universal.md](universal.md).

## Auth and access

- BLOCKER: new mutating endpoints without auth when siblings require auth
- BLOCKER: missing authorization check on user-scoped resources (IDOR patterns)
- REQUIRED: session/binding hooks and docs agree on writable vs read-only paths

## Injection and input

- BLOCKER: SQL/shell/LDAP/OS command built from user input
- BLOCKER: unsafe deserialization (`pickle`, `yaml.load` without SafeLoader) on untrusted data
- REQUIRED: path traversal in user-influenced file paths or codenames without validation

## Secrets and crypto

- BLOCKER: hardcoded credentials, tokens, private keys (committed credential hygiene — see [leaks.md](leaks.md) when `triggers.leaks`; this agent owns exploit path and access-control when `triggers.security`)
- REQUIRED: secrets in logs or error messages
- Flag weak crypto, disabled TLS verification on production paths

## Dependencies and supply chain

- REQUIRED: unpinned new runtime deps in changeset — note audit tool if run; do not invent CVEs

## Agent-specific

- Cite `file:line` and attack scenario in one sentence
- Map to confidence HIGH only when exploit path is clear
