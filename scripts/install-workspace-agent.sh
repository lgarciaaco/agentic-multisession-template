#!/usr/bin/env bash
# Install a per-project agent launcher on PATH (~/.local/bin).
# Each hub gets its own command (e.g. my-app → my-agent) and config dir.
set -euo pipefail

HUB="$(cd "$(dirname "$0")/.." && pwd)"
SLUG="${WORKSPACE_HUB_SLUG:-$(basename "$HUB")}"
BIN_DIR="${WORKSPACE_BIN_DIR:-$HOME/.local/bin}"

_name_ok() {
  [[ "$1" =~ ^[a-zA-Z0-9._-]+$ ]]
}

if ! _name_ok "$SLUG"; then
  echo "Error: invalid hub slug '$SLUG' (use letters, digits, . _ - only)" >&2
  exit 1
fi

if [[ -n "${WORKSPACE_AGENT_LAUNCHER:-}" ]]; then
  LAUNCHER="$WORKSPACE_AGENT_LAUNCHER"
elif [[ "$SLUG" == *-agent ]]; then
  LAUNCHER="$SLUG"
else
  LAUNCHER="${SLUG%%-*}-agent"
fi

if ! _name_ok "$LAUNCHER"; then
  echo "Error: invalid launcher name '$LAUNCHER' (use letters, digits, . _ - only)" >&2
  exit 1
fi
if [[ "$LAUNCHER" == *"/"* || "$LAUNCHER" == *".."* ]]; then
  echo "Error: launcher must be a single path segment" >&2
  exit 1
fi

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/${SLUG}"
WRAPPER="$BIN_DIR/${LAUNCHER}"

mkdir -p "$CONFIG_DIR" "$BIN_DIR"
printf '%s\n' "$HUB" > "$CONFIG_DIR/hub"
printf '%s\n' "$SLUG" > "$CONFIG_DIR/slug"
printf '%s\n' "$LAUNCHER" > "$HUB/.hub-launcher"
printf '%s\n' "$SLUG" > "$HUB/.hub-slug"

# CONFIG_DIR is safe to embed: SLUG validated to [a-zA-Z0-9._-]+
cat > "$WRAPPER" <<EOF
#!/usr/bin/env bash
# Hub agent launcher — $LAUNCHER (hub slug: $SLUG)
# Installed by $HUB/scripts/install-workspace-agent.sh
set -euo pipefail

CONFIG_DIR='${CONFIG_DIR}'
hub="\${WORKSPACE_ROOT:-}"
if [[ -z "\$hub" && -f "\$CONFIG_DIR/hub" ]]; then
  hub="\$(< "\$CONFIG_DIR/hub")"
fi
if [[ -z "\$hub" || ! -d "\$hub" ]]; then
  slug="\$(< "\$CONFIG_DIR/slug" 2>/dev/null || echo '$SLUG')"
  echo "Error: hub '\$slug' not found. Set WORKSPACE_ROOT or re-run:" >&2
  echo "  $HUB/scripts/install-workspace-agent.sh" >&2
  exit 1
fi
export WORKSPACE_ROOT="\$hub"
# shellcheck disable=SC1091
source "\$hub/scripts/lib/hub-env.sh"
ensure_tmux_window_prefix "\$(hub_slug_from_root "\$hub")"

exec "\$hub/scripts/workspace-agent.sh" "\$@"
EOF

chmod +x "$WRAPPER"
chmod +x "$HUB"/scripts/*.sh

echo "Installed: $WRAPPER"
echo "Command:   $LAUNCHER"
echo "Hub:       $HUB"
echo "Config:    $CONFIG_DIR/hub"
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  echo ""
  echo "Add to PATH (e.g. in ~/.bashrc):"
  echo "  export PATH=\"$BIN_DIR:\$PATH\""
fi
echo ""
echo "Usage from anywhere: $LAUNCHER"
