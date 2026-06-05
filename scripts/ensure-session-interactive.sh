#!/usr/bin/env bash
# Resolve or interactively pick a session for this tab.
set -euo pipefail
# shellcheck source=lib/hub-cli.sh
source "$(cd "$(dirname "$0")" && pwd)/lib/hub-cli.sh"
hub_cli ensure "$@"
