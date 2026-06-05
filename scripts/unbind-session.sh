#!/usr/bin/env bash
# Clear chat and tmux pane binding (does not close session work).
set -euo pipefail
# shellcheck source=lib/hub-cli.sh
source "$(cd "$(dirname "$0")" && pwd)/lib/hub-cli.sh"
hub_cli unbind "$@"
