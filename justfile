# List recipes.
default:
  @just --list

# --- Bash helpers ---------------------------------------------------------

[private]
_require_cmd := '''
  require_cmd() {
    command -v "$1" >/dev/null 2>&1 || {
      printf 'Required command not found: %s\n' "$1" >&2
      exit 1
    }
  }
'''

# --- Recipe helpers -------------------------------------------------------

# Run a root package script.
[private]
_pnpm_run SCRIPT:
  #!/usr/bin/env bash
  set -euo pipefail
  {{ _require_cmd }}

  require_cmd pnpm
  pnpm run {{ quote(SCRIPT) }}

# --- Workspace ------------------------------------------------------------

# Install from the lockfile.
install_frozen: (_pnpm_run 'install:frozen')

# Install and update the lockfile.
install_unlock: (_pnpm_run 'install:unlock')

# Run every check; changes nothing.
check: check_root check_components check_contracts check_launcher check_server check_mcp_server

# Check justfile formatting.
check_justfile_format:
  @just --fmt --check --indentation '  '

# Format files.
format:
  #!/usr/bin/env bash
  set -euo pipefail
  {{ _require_cmd }}

  require_cmd pnpm
  pnpm run format
  pnpm run format:markdown

# Type-check the root tools.
typecheck: (_pnpm_run 'check:types')

# Test the root tools.
test: (_pnpm_run 'test')

# Unstage *WORKING_NOTES*.md files.
unstage_working_notes:
  #!/usr/bin/env bash
  set -euo pipefail
  {{ _require_cmd }}

  require_cmd git
  git diff --cached --name-only -z -- ':(glob)**/*WORKING_NOTES*.md' \
    | while IFS= read -r -d '' path; do
        git reset -q -- "${path}"
        printf 'unstaged %s\n' "${path}" >&2
      done

# --- Root -----------------------------------------------------------------

# Check the repo root: format, justfile, Markdown, YAML, README maps, modules, placeholders, ports, types, tools.
check_root:
  pnpm run check
  uv run --locked yamllint --strict .

# Check the loopback ports agree across modules.
check_ports:
  node tools/ports/check-ports.ts .

# --- components -----------------------------------------------------------

# Lint and type-check components; check visual tokens and DESIGN.md are current.
check_components: check_visual_tokens
  pnpm --filter components --fail-if-no-match run check

# Generate visual tokens and DESIGN.md front matter.
generate_visual_tokens:
  node tools/visual-tokens/generate-visual-tokens.ts --tokens components/design/visual-tokens.json --out components/generated --design DESIGN.md --dark class

# Check visual tokens and DESIGN.md front matter are current.
check_visual_tokens:
  node tools/visual-tokens/generate-visual-tokens.ts --tokens components/design/visual-tokens.json --out components/generated --design DESIGN.md --dark class --check

# Vendor shadcn components into components/component-core/.
add_shadcn_atoms UI_NAME='' OVERWRITE='false' BASE='base-vega':
  #!/usr/bin/env bash
  #
  # Inputs:
  #   UI_NAME    component to add, e.g. dialog; space-separated for several
  #   OVERWRITE  replace the file when one already exists
  #   BASE       shadcn style token, `<primitive base>-<visual style>`
  #
  # Behavior:
  #   - Dies when BASE and the components/components.json `style` differ
  #   - Runs the shadcn CLI pinned in the root package.json against components/
  #   - Rewrites generated `@/` imports to relative paths, then formats components/
  #
  # Notes:
  #   - `shadcn add` takes no base flag. The CLI reads it from components.json
  #   - An unpinned CLI rewrites the style on Tailwind v4; Renovate moves the pin
  #   - Every layer file sits one folder deep, so `@/<dir>/` becomes `../<dir>/`.
  #     An app's own `@/` alias points at its src/, not at components/
  #   - The rewrite is idempotent and skips comment lines
  #
  # Examples:
  #   just add_shadcn_atoms dialog
  #   just add_shadcn_atoms dialog true
  #   just add_shadcn_atoms 'dialog drawer sheet' true base-vega
  #
  set -euo pipefail
  {{ _require_cmd }}

  die() {
    printf '\nERROR: %s\n\n' "$*" >&2
    exit 2
  }
  require_cmd pnpm
  require_cmd jq
  require_cmd perl

  UI_NAME={{ quote(UI_NAME) }}
  OVERWRITE={{ quote(OVERWRITE) }}
  BASE={{ quote(BASE) }}

  [[ -n "${UI_NAME}" ]] || die "Must provide UI_NAME, e.g. just add_shadcn_atoms dialog"
  [[ -n "${BASE}" ]] || die "Must specify BASE, e.g. just add_shadcn_atoms dialog false base-vega"
  configured="$(jq -r '.style // empty' components/components.json)"
  [[ -n "${configured}" ]] || die "components.json states no style; the base must be stated, not inferred."
  [[ "${configured}" == "${BASE}" ]] || die "components.json states style '${configured}', BASE is '${BASE}'."

  flags=()
  case "$(printf '%s' "${OVERWRITE}" | tr '[:upper:]' '[:lower:]')" in
    1|true|yes|y|on) flags+=(--overwrite) ;;
    0|false|no|n|off|"") ;;
    *) die "Invalid boolean value: ${OVERWRITE} (use true|false)" ;;
  esac

  read -r -a names <<< "${UI_NAME}"
  pnpm exec shadcn add --cwd components "${names[@]}" ${flags[@]+"${flags[@]}"}

  dirs=()
  for dir in component-core component-elements component-patterns lib hooks; do
    [[ -d "components/${dir}" ]] && dirs+=("components/${dir}")
  done
  find "${dirs[@]}" -type f \( -name '*.ts' -o -name '*.tsx' \) -exec perl -pi -e \
    'next if /^\s*\/\//; s/((?:from|import)\s+["\x27])\@\/(component-core|component-elements|component-patterns|lib|hooks)\//$1..\/$2\//g' {} +
  pnpm exec prettier --write components/ >/dev/null

  echo "Added ${UI_NAME} against base '${BASE}'."

# --- contracts ------------------------------------------------------------

# Lint contracts and run their conformance suites.
check_contracts:
  pnpm --filter contracts --fail-if-no-match run lint
  node tools/conformance/check-conformance.ts contracts

# Copy the knowledge-bus protocol, universe, and type guidance at REF into contracts/.
refresh_knowledge_model REF='main':
  node tools/knowledge-model/refresh-knowledge-model.ts --ref {{ quote(REF) }} --dest contracts/extensions/knowledge-bus/upstream

# --- launcher -------------------------------------------------------------

# Lint, type-check, test, and format-check the launcher UI.
check_launcher:
  pnpm --filter launcher --fail-if-no-match run check

# Build the sidecars, then the launcher app and DMG.
build_launcher: build_sidecars
  pnpm --filter launcher --fail-if-no-match exec tauri build --bundles app,dmg

# Build the sidecars, then a signed, notarized, and verified launcher DMG.
release_launcher: build_sidecars
  bash launcher/scripts/release-build.sh

# --- server ---------------------------------------------------------------

# Lint, format-check, and test server, with the vendored knowledge model.
check_server:
  uv run --locked ruff check server
  uv run --locked ruff format --check server
  cd server && KM_KNOWLEDGE_MODEL_DIR=../contracts/extensions/knowledge-bus/upstream uv run --locked pytest

# --- mcp-server -----------------------------------------------------------

# Lint, format-check, and test mcp-server; check the tools doc is current.
check_mcp_server: check_mcp_tools_doc
  uv run --locked ruff check mcp-server
  uv run --locked ruff format --check mcp-server
  cd mcp-server && uv run --locked pytest

# Write the intro and the tool tables in docs/mcp-tools.md from the server's code.
generate_mcp_tools_doc:
  uv run --locked --package mcp-server python mcp-server/scripts/generate_tools_doc.py docs/mcp-tools.md

# Check the intro and the tool tables in docs/mcp-tools.md are current.
check_mcp_tools_doc:
  uv run --locked --package mcp-server python mcp-server/scripts/generate_tools_doc.py docs/mcp-tools.md --check

# --- Sidecars -------------------------------------------------------------

# Check the ports, then freeze server and mcp-server into launcher/src-tauri/binaries/; server bundles the vendored knowledge model.
build_sidecars: check_ports
  #!/usr/bin/env bash
  set -euo pipefail
  {{ _require_cmd }}

  # Homebrew rustup may be absent from PATH; rustc supplies the target triple.
  if ! command -v rustc >/dev/null 2>&1 && [[ -d /opt/homebrew/opt/rustup/bin ]]; then
    export PATH="/opt/homebrew/opt/rustup/bin:${PATH}"
  fi
  require_cmd uv
  require_cmd rustc
  triple="$(rustc --print host-tuple)"
  out=launcher/src-tauri/binaries
  mkdir -p "${out}"

  (cd server && uv run --locked --exact --package server --group build \
    pyinstaller --noconfirm --clean km-server.spec \
    -- --knowledge-model-dir ../contracts/extensions/knowledge-bus/upstream)
  (cd mcp-server && uv run --locked --exact --package mcp-server --group build \
    pyinstaller --noconfirm --clean km-mcp.spec)

  cp server/dist/km-server "${out}/km-server-${triple}"
  cp mcp-server/dist/km-mcp "${out}/km-mcp-${triple}"
  chmod +x "${out}/km-server-${triple}" "${out}/km-mcp-${triple}"
  for binary in "${out}/km-server-${triple}" "${out}/km-mcp-${triple}"; do
    file "${binary}"
    codesign -dv "${binary}" 2>&1 | grep -E 'Signature|Identifier' || true
  done

# --- Docs -----------------------------------------------------------------

# Fill the root README module maps from each module README.
generate_readme_maps:
  node tools/readme-regions/sync-readme-regions.ts README.md

# Check the root README module maps are current.
check_readme_maps:
  node tools/readme-regions/sync-readme-regions.ts README.md --check

# --- Dependencies ---------------------------------------------------------

# Scan lockfiles for vulnerabilities.
scan_dependencies:
  #!/usr/bin/env bash
  set -euo pipefail
  {{ _require_cmd }}

  require_cmd osv-scanner
  require_cmd node
  node tools/dependencies/scan-dependencies.ts

# Scan lockfiles; warn if OSV is unreachable.
scan_dependencies_or_warn:
  #!/usr/bin/env bash
  set -euo pipefail
  {{ _require_cmd }}

  require_cmd osv-scanner
  require_cmd node
  stderr_file="$(mktemp)"
  trap 'rm -f "${stderr_file}"' EXIT
  set +e
  node tools/dependencies/scan-dependencies.ts 2>"${stderr_file}"
  status=$?
  set -e
  if [[ "${status}" -eq 127 ]] && grep -qE 'error when retrieving vulns|request failed|dial tcp|no such host|i/o timeout|TLS handshake' "${stderr_file}"; then
    printf 'warning: osv-scanner could not reach the OSV API; continuing without a vulnerability scan.\n' >&2
    exit 0
  fi
  cat "${stderr_file}" >&2
  exit "${status}"

# Validate renovate.json.
check_renovate_config:
  #!/usr/bin/env bash
  set -euo pipefail
  {{ _require_cmd }}

  require_cmd renovate-config-validator
  renovate-config-validator renovate.json
