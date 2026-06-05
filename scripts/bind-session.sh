#!/usr/bin/env bash
# Bind session to this chat and/or tmux pane.
set -euo pipefail
# shellcheck source=lib/hub-cli.sh
source "$(cd "$(dirname "$0")" && pwd)/lib/hub-cli.sh"
hub_cli bind "$@"
