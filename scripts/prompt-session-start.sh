#!/usr/bin/env bash
# Agent-facing session picker text (IDE hooks / orchestrator).
set -euo pipefail
exec "$(cd "$(dirname "$0")" && pwd)/list-active-sessions.sh" prompt
