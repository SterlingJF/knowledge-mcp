#!/usr/bin/env -S just --justfile

# This file is at root of monorepo
# File: justfile

# --- General Bash helpers ---------------------------------------------------------

# Bash helper: die with error message and exit code 2.
die := '''
  die() {
    printf '\nERROR: %s\n\n' "$*" >&2
    exit 2
  }
'''

# Bash helper: evaluate a common boolean-like value as a shell predicate.
_bool_is_true := '''
_bool_is_true() {
  local VALUE="${1:-false}"

  case "${VALUE,,}" in
    1|true|yes|y|on)        return 0 ;;
    0|false|no|n|off|"")    return 1 ;;
    *) die "Invalid boolean value: ${VALUE} (use true|false)" ;;
  esac
}
'''

# Bash helper: require a command is available.
_require_cmd := '''
_require_cmd() {
  local CMD="$1"
  command -v "${CMD}" >/dev/null 2>&1 || die "Missing required command: ${CMD}"
}
'''

# --- Frontend [Component-Core Vendoring] Workflow -----------

# Add shadcn components to component-core, against a stated primitive base.
add_shadcn_atoms UI_NAME='' OVERWRITE='false' BASE='base-vega':
  #!/usr/bin/env bash
  #
  # Inputs:
  #   UI_NAME    component to add, e.g. dialog; space-separated for several
  #   OVERWRITE  replace the file when one already exists
  #   BASE       shadcn style token, `<primitive base>-<visual style>`
  #
  # Behavior:
  #   - Dies when BASE and the components.json `style` differ
  #   - Adds the components with a pinned shadcn CLI version
  #   - Normalizes generated local imports to the `@/` source alias
  #
  # Output:
  #   - Writes each component into the alias directory components.json names for its type
  #   - Prints the base the add ran against
  #
  # Notes:
  #   - `shadcn add` takes no base flag. The CLI reads it from components.json
  #   - CLI version is pinned. An unpinned CLI rewrites the style on Tailwind v4
  #   - Several names in one call re-vendor them against one CLI resolution
  #   - Alias rewrite is idempotent and skips comment lines
  #
  # Examples:
  #   just add_shadcn_atoms dialog
  #   just add_shadcn_atoms dialog true
  #   just add_shadcn_atoms dialog false base-vega
  #   just add_shadcn_atoms 'dialog drawer sheet' true base-vega
  #
  set -euo pipefail
  {{ die }}
  {{ _bool_is_true }}
  {{ _require_cmd }}

  SHADCN_PROJECT='launcher'
  SHADCN_CLI='shadcn@4.19.0'
  OVERWRITE="{{ OVERWRITE }}"
  UI_NAME="{{ UI_NAME }}"
  BASE="{{ BASE }}"
  typeset -a SHADCN_CMD_FLAGS=()

  _should_overwrite() {
    _bool_is_true "${OVERWRITE}"
  }

  _add_flag_if_needed() {
    if _should_overwrite; then
      SHADCN_CMD_FLAGS+=(--overwrite)
    fi
  }

  _configured_base() {
    jq -r '.style // empty' "${SHADCN_PROJECT}/components.json"
  }

  _check_base_is_pinned() {
    local configured
    configured="$(_configured_base)"

    [[ -n "${BASE}" ]] || die "Must specify BASE, e.g. just add_shadcn_atoms dialog false base-vega"
    [[ -n "${configured}" ]] || die "components.json states no style; the base must be stated, not inferred."
    [[ "${configured}" == "${BASE}" ]] || die "components.json states style '${configured}', BASE is '${BASE}'."
  }

  _add_shadcn_ui() {
    cd "${SHADCN_PROJECT}"

    if [[ -n "${UI_NAME}" ]]; then
      typeset -a UI_NAMES=()
      read -r -a UI_NAMES <<< "${UI_NAME}"
      pnpm dlx "${SHADCN_CLI}" add "${UI_NAMES[@]}" "${SHADCN_CMD_FLAGS[@]}"
    else
      echo "Must provide UI_NAME, e.g. just add_shadcn_atoms dialog"
      exit 1
    fi
  }

  _normalize_alias_imports() {
    typeset -a ALIAS_DIRS=(src/component-core src/component-elements src/component-patterns src/lib src/hooks)
    typeset -a TARGETS=()

    for dir in "${ALIAS_DIRS[@]}"; do
      [[ -d "${dir}" ]] || continue
      while IFS= read -r file; do
        TARGETS+=("${file}")
      done < <(find "${dir}" -type f \( -name '*.ts' -o -name '*.tsx' \))
    done

    [[ "${#TARGETS[@]}" -gt 0 ]] || return 0

    perl -pi -e 'next if /^\s*\/\//; s/((?:from|import)\s+["\x27])\.\.\/(component-core|component-elements|component-patterns|components|lib|hooks)\//$1\@\/$2\//g' "${TARGETS[@]}"

    echo "    OK: local imports normalized to @/."
  }

  _checks() {
    echo ""
    echo ">>> Checks"

    _require_cmd pnpm
    _require_cmd jq
    _require_cmd perl
    [[ -n "${SHADCN_PROJECT}" ]] || die "Must specify Shadcn project folder."
    [[ -d "${SHADCN_PROJECT}" ]] || die "Shadcn project not found: ${SHADCN_PROJECT}"
    _check_base_is_pinned

    echo "    OK: pnpm present, shadcn project found."
    echo "    OK: base '${BASE}', CLI ${SHADCN_CLI}."
  }

  _main() {
    _checks
    _add_flag_if_needed
    _add_shadcn_ui
    _normalize_alias_imports
  }

  _main
