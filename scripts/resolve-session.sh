#!/usr/bin/env bash
# Print resolved session codename (chat binding → tmux pane → window name).
set -euo pipefail
# shellcheck source=lib/hub-cli.sh
source "$(cd "$(dirname "$0")" && pwd)/lib/hub-cli.sh"
hub_cli resolve "$@"
