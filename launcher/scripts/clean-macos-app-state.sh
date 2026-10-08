#!/usr/bin/env bash
# File: launcher/scripts/clean-macos-app-state.sh

set -euo pipefail

LAUNCHER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TAURI_DIR="${LAUNCHER_DIR}/src-tauri"
TARGET_DIR="${TAURI_DIR}/target"
INSTALLED_APP="/Applications/Knowledge MCP.app"
APP_BUNDLE_ID="com.sterlingjf.knowledge-mcp"
LSREGISTER="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
MODE="${1:-all}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "ERROR: macOS app cleanup can only run on macOS." >&2
  exit 2
fi

if [[ "${MODE}" != "all" && "${MODE}" != "--generated-only" ]]; then
  echo "Usage: $0 [--generated-only]" >&2
  exit 2
fi

bundle_id() {
  /usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$1/Contents/Info.plist" 2>/dev/null
}

is_knowledge_mcp() {
  [[ -d "$1" ]] && [[ "$(bundle_id "$1" || true)" == "${APP_BUNDLE_ID}" ]]
}

unregister() {
  local app="$1"

  echo ">>> Unregistering: ${app}"
  if ! "${LSREGISTER}" -u "${app}"; then
    echo "WARNING: LaunchServices could not unregister ${app}; continuing with scoped cleanup." >&2
  fi
}

cleanup_generated_apps() {
  local app

  [[ -d "${TARGET_DIR}" ]] || return 0

  while IFS= read -r -d '' app; do
    if ! is_knowledge_mcp "${app}"; then
      echo "ERROR: refusing to remove generated app with an unexpected bundle identifier: ${app}" >&2
      exit 2
    fi

    unregister "${app}"
    echo ">>> Removing generated app: ${app}"
    rm -rf "${app}"
  done < <(find "${TARGET_DIR}" -type d -path '*/bundle/macos/Knowledge MCP.app' -prune -print0)
}

cleanup_mounted_apps() {
  local app volume

  for app in /Volumes/*/Knowledge\ MCP.app; do
    [[ -d "${app}" ]] || continue
    is_knowledge_mcp "${app}" || continue

    volume="${app%/Knowledge MCP.app}"
    unregister "${app}"
    echo ">>> Ejecting: ${volume}"
    hdiutil detach "${volume}"
  done
}

registered_app_paths() {
  "${LSREGISTER}" -dump | awk -v expected_id="${APP_BUNDLE_ID}" '
    function emit() {
      if (identifier == expected_id && path) print path
    }
    /^bundle id:/ {
      emit()
      identifier = ""
      path = ""
    }
    /^path:/ {
      path = $0
      sub(/^path:[[:space:]]*/, "", path)
      sub(/[[:space:]]+\(0x[[:xdigit:]]+\)$/, "", path)
    }
    /^identifier:/ {
      identifier = $0
      sub(/^identifier:[[:space:]]*/, "", identifier)
    }
    END { emit() }
  '
}

cleanup_other_registrations() {
  local app

  while IFS= read -r app; do
    [[ -n "${app}" ]] || continue
    [[ "${app}" == "${INSTALLED_APP}" ]] && continue
    unregister "${app}"
  done < <(registered_app_paths)
}

launch_services_flags() {
  local app="$1"

  "${LSREGISTER}" -dump | awk -v expected="${app}" '
    /^bundle id:/ { matches_path = 0 }
    /^path:/ {
      path = $0
      sub(/^path:[[:space:]]*/, "", path)
      sub(/[[:space:]]+\(0x[[:xdigit:]]+\)$/, "", path)
      matches_path = path == expected
    }
    matches_path && /^bundle flags:/ && !flags { flags = $0 }
    END { if (flags) print flags }
  '
}

restore_installed_app() {
  local flags

  if [[ ! -d "${INSTALLED_APP}" ]]; then
    echo ">>> No installed app to restore at ${INSTALLED_APP}"
    return 0
  fi

  if ! is_knowledge_mcp "${INSTALLED_APP}"; then
    echo "ERROR: refusing to register an installed app with an unexpected bundle identifier." >&2
    exit 2
  fi

  echo ">>> Registering installed app: ${INSTALLED_APP}"
  "${LSREGISTER}" -f "${INSTALLED_APP}"
  "${LSREGISTER}" -gc

  flags="$(launch_services_flags "${INSTALLED_APP}")"
  if [[ -z "${flags}" ]]; then
    echo "ERROR: LaunchServices has no record for ${INSTALLED_APP}." >&2
    exit 1
  fi
  if [[ "${flags}" == *launch-disabled* ]]; then
    if xattr -p com.apple.quarantine "${INSTALLED_APP}" >/dev/null 2>&1; then
      echo ">>> Installed app awaits normal first-launch approval: ${flags}"
      return 0
    fi

    echo "ERROR: installed, non-quarantined app remains launch-disabled: ${flags}" >&2
    exit 1
  fi

  echo ">>> Installed app is enabled: ${flags}"
}

cleanup_generated_apps
"${LSREGISTER}" -gc

if [[ "${MODE}" == "all" ]]; then
  cleanup_mounted_apps
fi

cleanup_other_registrations
"${LSREGISTER}" -gc

if [[ "${MODE}" == "all" ]]; then
  restore_installed_app
fi
