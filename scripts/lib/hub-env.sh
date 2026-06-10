# Shared hub environment defaults (source from workspace-agent.sh / installed launcher).
# shellcheck shell=bash

hub_slug_from_root() {
  local hub="$1"
  if [[ -n "${WORKSPACE_HUB_SLUG:-}" ]]; then
    printf '%s' "$WORKSPACE_HUB_SLUG"
    return
  fi
  if [[ -f "$hub/.hub-slug" ]]; then
    tr -d '\n' <"$hub/.hub-slug"
    return
  fi
  basename "$hub"
}

default_tmux_window_prefix() {
  local slug="$1"
  local stem
  if [[ -z "$slug" ]]; then
    return
  fi
  if [[ "$slug" == *-agent ]]; then
    slug="${slug%-agent}"
  fi
  if [[ "$slug" == *-* ]]; then
    stem="${slug%%-*}"
  else
    stem="$slug"
  fi
  printf '%s-' "$stem"
}

# Set WORKSPACE_TMUX_WINDOW_PREFIX from hub slug (always refresh unless explicitly disabled).
ensure_tmux_window_prefix() {
  local slug="$1"
  if [[ "${WORKSPACE_TMUX_WINDOW_PREFIX+x}" == "x" && "${WORKSPACE_TMUX_WINDOW_PREFIX}" == "" ]]; then
    return
  fi
  WORKSPACE_TMUX_WINDOW_PREFIX="$(default_tmux_window_prefix "$slug")"
  export WORKSPACE_TMUX_WINDOW_PREFIX
}
