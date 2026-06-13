# Leaks rules (committed secrets and sensitive data)

Deep pass for repo hygiene in the changeset. Runs on most `changeset` and `task` reviews. The optional **security-reviewer** owns auth, injection, and access-control design — this agent owns data that should not be committed.

## Secrets and credentials

- BLOCKER: hardcoded API keys, tokens, passwords, or private keys (PEM blocks, `BEGIN PRIVATE KEY`, AWS/GCP/Azure access patterns)
- BLOCKER: `.env`, credentials files, or kubeconfig fragments committed to the repo
- REQUIRED: high-entropy strings resembling tokens in source, tests, or fixtures without redaction or env indirection
- REQUIRED: secrets echoed in log statements, error messages, or debug output in changed files

## Identifiers and PII

- BLOCKER: committed personal email, phone, government ID, or full street address in non-fixture production paths
- REQUIRED: hardcoded real person names or org-specific hostnames/accounts when generic placeholders suffice
- REQUIRED: PII in test fixtures without `example.com` / synthetic-data markers or documented test-only scope
- SUGGESTION: internal codenames or customer names in comments when they could leak context in a public fork

## Vulnerability hints in diff

- REQUIRED: obvious SQL/shell injection strings left in committed examples that look like live queries
- REQUIRED: disabled TLS verification (`verify=False`, `NODE_TLS_REJECT_UNAUTHORIZED=0`) on non-test paths
- REQUIRED: `pickle.loads`, `yaml.load` without SafeLoader, or `eval` on untrusted input in new code
- SUGGESTION: commented-out credentials or URLs that look production-like

## Scope

- Review manifest delta files only; do not scan entire repo history
- Do not invent CVEs or run dependency audit tools — flag only what is visible in the changeset
- Cite `file:line` and one sentence on exposure (public fork, log leak, committed credential)

## Split from security-reviewer

| leaks-reviewer | security-reviewer |
|----------------|-------------------|
| Committed secrets, keys, PII, hygiene in diff | Authz, injection design, IDOR, endpoint protection |
| `triggers.leaks` | `triggers.security` |

Overlap on hardcoded credentials: **leaks-reviewer** owns committed credential hygiene; **security-reviewer** owns exploit path and access-control context when security paths are in scope.

## Severity

BLOCKER allowed for committed live credentials or private keys. Synthesizer maps BLOCKER from this agent to FAIL.
