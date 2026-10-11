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
check: check_root check_contracts check_runtime

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

# Check the repo root: format, justfile, Markdown, YAML, README maps, modules, placeholders, types, tools.
check_root:
  pnpm run check
  uv run --locked yamllint --strict .

# --- contracts ------------------------------------------------------------

# Lint contracts and run their conformance suites.
check_contracts:
  pnpm --filter contracts --fail-if-no-match run lint
  node tools/conformance/check-conformance.ts contracts

# --- runtime -------------------------------------------------------------

# Lint, format-check, and test runtime; check the tools doc and the plugin's lock are current.
check_runtime: check_mcp_tools_doc check_knowledge_mcp_lock
  uv run --locked ruff check runtime
  uv run --locked ruff format --check runtime
  cd runtime && uv run --locked pytest

# Write runtime/requirements.lock, the hashed lock the installed plugin runs from, from uv.lock.
generate_knowledge_mcp_lock:
  uv export --locked --quiet --package knowledge-mcp --no-dev --no-emit-workspace --no-header --format requirements-txt > runtime/requirements.lock

# Check runtime/requirements.lock is in step with uv.lock.
check_knowledge_mcp_lock:
  #!/usr/bin/env bash
  set -euo pipefail
  if ! diff -u runtime/requirements.lock <(uv export --locked --quiet --package knowledge-mcp --no-dev --no-emit-workspace --no-header --format requirements-txt); then
    printf '\nruntime/requirements.lock is stale; run just generate_knowledge_mcp_lock.\n' >&2
    exit 1
  fi

# Copy knowledge-bus's universe specs and skills at TAG into runtime; TAG must be the tag of the pinned release archive.
refresh_knowledge_model TAG:
  node tools/knowledge-model/refresh-knowledge-model.ts --ref {{ quote(TAG) }} --plugin runtime

# Write the intro and the tool tables in docs/mcp-tools.md from the server's code.
generate_mcp_tools_doc:
  uv run --locked --package knowledge-mcp python runtime/scripts/generate_tools_doc.py docs/mcp-tools.md

# Check the intro and the tool tables in docs/mcp-tools.md are current.
check_mcp_tools_doc:
  uv run --locked --package knowledge-mcp python runtime/scripts/generate_tools_doc.py docs/mcp-tools.md --check

# Build dist/knowledge_mcp-<version>.tar.gz, the source archive the Homebrew formula installs.
build_knowledge_mcp:
  uv build --package knowledge-mcp --sdist --out-dir dist

# Write the Homebrew formula for SDIST, a built source archive, from uv.lock; nothing is published.
generate_formula SDIST OUT='dist/knowledge-mcp.rb':
  mkdir -p "$(dirname {{ quote(OUT) }})"
  node tools/formula/generate-formula.ts --sdist {{ quote(SDIST) }} --out {{ quote(OUT) }}

# --- Docs -----------------------------------------------------------------

# Fill the contributor guide module maps from each module README.
generate_readme_maps:
  node tools/readme-regions/sync-readme-regions.ts CONTRIBUTING.md

# Check the contributor guide module maps are current.
check_readme_maps:
  node tools/readme-regions/sync-readme-regions.ts CONTRIBUTING.md --check

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
