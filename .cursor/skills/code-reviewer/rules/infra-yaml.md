# Infra YAML rules (Ansible, GitHub Actions, deploy manifests)

Deep pass for infrastructure-as-code in the changeset. Code and security agents apply light config checks only; this agent owns Ansible idempotency, GHA trigger semantics, and deploy pipeline correctness.

## Ansible

- BLOCKER: tasks that regenerate secrets or overwrite live config on every run (password rotation without `--rotate` flag, unconditional `template` to secrets paths)
- REQUIRED: `git` module without `force: true` when playbook re-runs on servers with local drift or dirty trees
- REQUIRED: `command`/`shell` tasks without `creates`, `removes`, or `changed_when` when a module exists or idempotency is unclear
- REQUIRED: env or config template changes without handler to restart dependent services (Docker stack, systemd units, reverse proxy)
- REQUIRED: deprecated `apt_key` or GPG keyring path mismatch on modern Debian/Ubuntu (use `get_url` + `gpg --dearmor` to signed-by keyring)
- REQUIRED: handler gaps — notify on config change but no handler defined, or handler never flushed
- SUGGESTION: health/retry timeouts too short for cold Docker builds on first bootstrap
- SUGGESTION: role ordering that runs app before dependencies (Docker, packages) are ready

## GitHub Actions

- REQUIRED: `workflow_run` deploy jobs that checkout `main` instead of `github.event.workflow_run.head_sha` — race with newer merges
- REQUIRED: missing concurrency guard or wrong `cancel-in-progress` on long-running deploy jobs (can abort mid-deploy)
- REQUIRED: deploy workflow without syntax validation in CI (actionlint, ansible-lint, or syntax-check job)
- SUGGESTION: SSH deploy without post-deploy health check in the remote script
- SUGGESTION: secrets passed via env without documenting rotation or idempotent setup

## Shell deploy scripts

- BLOCKER: setup scripts that overwrite production secrets on re-run without explicit rotate flag
- REQUIRED: remote deploy script exits 0 without verifying service health (`/health`, compose ps, systemd active)
- REQUIRED: bootstrap loops that do not surface Ansible failure output
- SUGGESTION: hardcoded host paths without variable or documented override

## Systemd and timers

- REQUIRED: timer `enabled: true` with service `state: stopped` without documenting expected post-reboot behavior
- SUGGESTION: worker/env files required at runtime not validated before enabling units

## Scope

- Review manifest files matching `deploy/**`, `.github/workflows/**`, `**/ansible/**`, and related shell in delta
- Do not invent CVEs or cloud-specific compliance frameworks
- Cite `file:line` and concrete failure scenario (bootstrap re-run, concurrent merge, secret rotation)

## Severity

BLOCKER allowed for live-stack breakage (secret overwrite, destructive unconditional tasks). Synthesizer maps BLOCKER from this agent to FAIL.
