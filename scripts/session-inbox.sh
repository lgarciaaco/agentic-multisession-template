#!/usr/bin/env bash
# Cross-session inbox: write from one codename to another's inbox file.
set -euo pipefail
# shellcheck source=lib/hub-cli.sh
source "$(cd "$(dirname "$0")" && pwd)/lib/hub-cli.sh"

cmd="${1:-}"
shift || true

case "$cmd" in
  write)
    if [[ $# -lt 3 ]]; then
      echo "Usage: $0 write <from> <to> <message>" >&2
      exit 1
    fi
    from="$1"
    to="$2"
    shift 2
    hub_cli inbox write "$from" "$to" "$*"
    ;;
  read)
    if [[ $# -lt 1 ]]; then
      echo "Usage: $0 read <codename>" >&2
      exit 1
    fi
    hub_cli inbox read "$1"
    ;;
  *)
    echo "Usage:" >&2
    echo "  $0 write <from> <to> <message>   # e.g. bravo → alpha" >&2
    echo "  $0 read <codename>" >&2
    exit 1
    ;;
esac
