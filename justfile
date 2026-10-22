# List recipes.
default:
  @just --list

[private]
_require_cmd := '''
  require_cmd() {
    command -v "$1" >/dev/null 2>&1 || {
      printf 'Required command not found: %s\n' "$1" >&2
      exit 1
    }
  }
'''

# Install the Node dependencies from pnpm-lock.yaml, and the Git hooks.
install_frozen:
  pnpm install --frozen-lockfile

# Install the Node dependencies and update pnpm-lock.yaml.
install_unlock:
  pnpm install --no-frozen-lockfile

# Run the CI checks without changing files.
check: check_root check_contracts check_runtime

# Check justfile formatting.
check_justfile_format:
  @just --fmt --check --indentation '  '

# Format and fix files with Prettier, markdownlint, just and ruff.
format:
  #!/usr/bin/env bash
  set -euo pipefail
  {{ _require_cmd }}

  require_cmd pnpm
  require_cmd uv
  pnpm run format
  pnpm run format:markdown
  just --fmt --indentation '  '
  uv run --locked ruff check --fix --exit-zero --quiet runtime
  uv run --locked ruff format runtime

# Run the pre-commit hooks on the staged files.
check_staged:
  uv run --locked pre-commit run

# Type-check tools/.
typecheck:
  pnpm run check:types

# Test tools/.
test:
  pnpm run test

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

# Install the Node dependencies when the last merge changed pnpm-lock.yaml, then scan the lockfiles.
post_merge:
  #!/usr/bin/env bash
  set -euo pipefail
  if git diff --name-only 'HEAD@{1}' HEAD 2>/dev/null | grep -qx 'pnpm-lock.yaml'; then
    pnpm install --frozen-lockfile --ignore-scripts
  fi
  just scan_dependencies_or_warn

# Run shellcheck on the Husky hooks and every bash recipe, after expanding the justfile variables.
[private]
_shellcheck:
  #!/usr/bin/env bash
  set -euo pipefail
  {{ _require_cmd }}

  require_cmd uv
  uv run --locked shellcheck --shell=sh .husky/pre-commit .husky/pre-push .husky/post-merge
  open='{'
  names() {
    just --dump --dump-format json | uv run --locked python -c "import json, sys; print(*json.load(sys.stdin)['$1'])"
  }
  declare -A values
  for variable in $(names assignments); do
    values["${variable}"]="$(just --evaluate "${variable}")"
  done
  failed=0
  for recipe in $(names recipes); do
    body="$(just --show "${recipe}")"
    [[ "${body}" == *'#!/usr/bin/env bash'* ]] || continue
    for variable in "${!values[@]}"; do
      body="${body//"${open}${open} ${variable} }}"/"${values[${variable}]}"}"
    done
    if ! printf '%s\n' "${body}" | sed -e '1,/#!\/usr\/bin\/env bash/d' -e 's/[{][{][^}]*[}][}]/placeholder/g' \
      | uv run --locked shellcheck --shell=bash -; then
      printf 'shellcheck failed for recipe %s\n' "${recipe}" >&2
      failed=1
    fi
  done
  exit "${failed}"

# Lint, format-check, type-check and test the root files and tools/. Check for unused code, the module layout, the Layout maps and the vendored knowledge-bus files.
check_root: check_justfile_format check_readme_maps _shellcheck
  pnpm run check
  pnpm exec knip --workspace .
  uv run --locked yamllint --strict .
  uv run --locked tombi lint ./*.toml runtime/pyproject.toml
  uv run --locked actionlint .github/workflows/ci.yml .github/workflows/release.yml
  node tools/knowledge-model/refresh-knowledge-model.ts --check --plugin runtime

# Lint the contract schemas and check the conformance samples and schema bundles.
check_contracts: (_contract_bundles 'check')
  #!/usr/bin/env bash
  set -euo pipefail
  mapfile -t openapi < <(find contracts -name '*.openapi.yaml' -not -path '*/node_modules/*' -not -path '*/upstream/*')
  if [[ ${#openapi[@]} -gt 0 ]]; then
    pnpm --dir contracts exec redocly lint --config redocly.yaml "${openapi[@]#contracts/}"
  else
    printf 'No OpenAPI files to lint.\n'
  fi
  # Skip description_trailing_period, because the schema descriptions end with a period.
  # Skip top_level_examples, because the conformance pass samples serve as examples.
  lint=(--resolve extensions/mcp/v1 --extension .schema.yaml --exclude description_trailing_period --exclude top_level_examples)
  schemas=()
  for schema in contracts/extensions/mcp/v1/*.schema.yaml; do
    case "${schema}" in
      */common.schema.yaml|*/document-types.schema.yaml) continue ;;
    esac
    schemas+=("${schema#contracts/}")
  done
  # List the schemas by path, because --ignore would also hide common.schema.yaml from the resolver.
  pnpm --dir contracts exec jsonschema lint "${lint[@]}" "${schemas[@]}"
  # common.schema.yaml holds only definitions that other schemas use, so skip orphan_definitions.
  pnpm --dir contracts exec jsonschema lint "${lint[@]}" --exclude orphan_definitions extensions/mcp/v1/common.schema.yaml
  # Skip the allOf rules, because the allOf in saved_entry shapes the generated classes.
  pnpm --dir contracts exec jsonschema lint "${lint[@]}" --exclude unnecessary_allof_wrapper --exclude unnecessary_allof_ref_wrapper_modern extensions/mcp/v1/document-types.schema.yaml
  schema_dir="$(mktemp -d)"
  trap 'rm -rf "${schema_dir}"' EXIT
    # $schema inside single quotes is a JSON key, not a shell variable.
  # shellcheck disable=SC2016
  uv run --locked python -c 'import json, pathlib, sys; folder = pathlib.Path(sys.argv[1]); tools = json.loads(pathlib.Path("contracts/extensions/mcp/v1/tools.json").read_text())["tools"]; [(folder / (tool["name"] + "-" + key + ".json")).write_text(json.dumps({"$schema": "https://json-schema.org/draft/2020-12/schema", **tool[key]})) for tool in tools for key in ("inputSchema", "outputSchema") if key in tool]' "${schema_dir}"
  # Pydantic emits redundant const and enum types, unused definitions, empty properties and allOf wrappers, so skip those rules.
  # tools.json keeps each tool description next to inputSchema, so skip top_level_description.
  pnpm --dir contracts exec jsonschema lint --exclude description_trailing_period --exclude top_level_examples --exclude const_with_type --exclude enum_with_type --exclude orphan_definitions --exclude properties_default --exclude top_level_description --exclude unnecessary_allof_wrapper --exclude unnecessary_allof_ref_wrapper_modern "${schema_dir}"
  node tools/conformance/check-conformance.ts contracts

contract_bundles := 'kbp-output folder-conventions convention-templates conventions conventions-update document-move document-moves document-type audiences import document-types-update edit edits document-types proposal problem'

# Generate runtime/knowledge_mcp/models_auto and schemas_auto from the contract schemas.
generate_contract_types: _contract_models (_contract_bundles 'write')

# Rewrite tools.json and the conformance pass samples from an in-process server.
generate_contract_snapshots:
  cd runtime && uv run --locked pytest -q tests/test_contract_snapshots.py --write-snapshots
  pnpm exec prettier --log-level warn --write contracts/extensions/mcp/v1/conformance/pass

[private]
_contract_models *FLAGS:
  #!/usr/bin/env bash
  set -euo pipefail
  # datamodel-codegen reads every file in its input folder, so copy only the schemas.
  schemas="$(mktemp -d)"
  trap 'rm -rf "${schemas}"' EXIT
  cp contracts/extensions/mcp/v1/*.schema.yaml "${schemas}/"
  if ! uv run --locked datamodel-codegen --input "${schemas}" {{ FLAGS }}; then
    printf '\ndatamodel-codegen failed. Review the error above.\n' >&2
    exit 1
  fi

[private]
_contract_bundles MODE:
  #!/usr/bin/env bash
  set -euo pipefail
  mode={{ quote(MODE) }}
  mkdir -p runtime/knowledge_mcp/schemas_auto
  for name in {{ contract_bundles }}; do
    bundle="runtime/knowledge_mcp/schemas_auto/${name}.schema.yaml"
    fresh="$(pnpm --dir contracts exec jsonschema bundle "extensions/mcp/v1/${name}.schema.yaml" --resolve extensions/mcp/v1 --extension .schema.yaml)"
    if [[ "${mode}" == write ]]; then
      printf '%s\n' "${fresh}" > "${bundle}"
    elif ! diff -u "${bundle}" <(printf '%s\n' "${fresh}"); then
      printf '\n%s is stale: run just generate_contract_types.\n' "${bundle}" >&2
      exit 1
    fi
  done

# Lint, type-check and test runtime/, and scan runtime/ for dead code. Check that models_auto and docs/mcp-tools.mdx are current.
check_runtime: check_mcp_tools_doc (_contract_models '--check')
  uv run --locked ruff check runtime
  uv run --locked ruff format --check runtime
  uv run --locked mypy
  uv run --locked vulture
  cd runtime && uv run --locked pytest -n auto --maxprocesses 4 --dist loadfile

# Copy the knowledge-bus universe specs and skills at TAG into runtime/. TAG must match the pin in runtime/pyproject.toml.
refresh_knowledge_model TAG:
  node tools/knowledge-model/refresh-knowledge-model.ts --ref {{ quote(TAG) }} --plugin runtime

# Write the generated regions of docs/mcp-tools.mdx from tools.json.
generate_mcp_tools_doc:
  uv run --locked --package knowledge-mcp python runtime/scripts/generate_tools_doc.py docs/mcp-tools.mdx

# Check the generated regions of docs/mcp-tools.mdx match tools.json.
check_mcp_tools_doc:
  uv run --locked --package knowledge-mcp python runtime/scripts/generate_tools_doc.py docs/mcp-tools.mdx --check

# Build the source archive that the Homebrew formula installs.
build_knowledge_mcp SOURCE='.' OUT='dist':
  uv build --project {{ quote(SOURCE) }} --package knowledge-mcp --sdist --out-dir {{ quote(OUT) }}

# Write the Homebrew formula for the source archive SDIST.
generate_formula SDIST OUT='dist/knowledge-mcp.rb' SOURCE='.':
  #!/usr/bin/env bash
  set -euo pipefail
  mkdir -p "$(dirname {{ quote(OUT) }})"
  requirements=$(mktemp)
  trap 'rm -f "$requirements"' EXIT
  uv export --color never --project {{ quote(SOURCE) }} --locked --package knowledge-mcp --no-dev --no-emit-workspace --no-header --format requirements-txt > "$requirements"
  node tools/formula/generate-formula.ts --sdist {{ quote(SDIST) }} --out {{ quote(OUT) }} --lock {{ quote(SOURCE + '/uv.lock') }} --requirements "$requirements" --pyproject {{ quote(SOURCE + '/runtime/pyproject.toml') }}

# Set the release version to VERSION in the manifests, CHANGELOG.md and uv.lock.
release_prepare VERSION:
  node tools/formula/release-metadata.ts prepare --version {{ quote(VERSION) }}

# Check the release versions, release notes and uv.lock.
release_check:
  uv lock --check
  node tools/formula/release-metadata.ts check

# Resolve the release TAG to its commit and write dist/release.json.
release_target TAG REPO='SterlingJF/knowledge-mcp':
  node tools/formula/release.ts target --tag {{ quote(TAG) }} --repo {{ quote(REPO) }}

# Download the source archive from the GitHub release, or build and upload it. Then write the formula.
release_source SOURCE='release-source':
  node tools/formula/release.ts source --release dist/release.json --source {{ quote(SOURCE) }}

# Build one native bottle, or download it when already published.
release_bottle ARCH PREFIX BOTTLE_TAG:
  node tools/formula/release.ts bottle --release dist/release.json --arch {{ quote(ARCH) }} --prefix {{ quote(PREFIX) }} --bottle-tag {{ quote(BOTTLE_TAG) }}

# Upload the bottles to the GitHub release and add the bottle block to the formula.
release_merge:
  node tools/formula/release.ts merge --release dist/release.json

# Install the formula from source and from the bottle. Time and test each install.
release_verify ARCH PREFIX BOTTLE_TAG:
  node tools/formula/release.ts verify --release dist/release.json --arch {{ quote(ARCH) }} --prefix {{ quote(PREFIX) }} --bottle-tag {{ quote(BOTTLE_TAG) }}

# Commit the formula to the tap checkout TAP and push the commit. Fail when the formula would downgrade the tap.
release_tap TAP='tap':
  node tools/formula/release.ts tap --release dist/release.json --tap {{ quote(TAP) }}

# Copy the Layout map of each module README into CONTRIBUTING.md.
generate_readme_maps:
  node tools/readme-regions/sync-readme-regions.ts CONTRIBUTING.md

# Check the Layout maps in CONTRIBUTING.md match the module READMEs.
check_readme_maps:
  node tools/readme-regions/sync-readme-regions.ts CONTRIBUTING.md --check

# Scan lockfiles for vulnerabilities.
scan_dependencies:
  #!/usr/bin/env bash
  set -euo pipefail
  {{ _require_cmd }}

  require_cmd osv-scanner
  require_cmd node
  node tools/dependencies/scan-dependencies.ts

# Scan lockfiles for vulnerabilities. Pass with a warning when the OSV API is unreachable.
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
    printf 'warning: osv-scanner could not reach the OSV API. Skipping the vulnerability scan.\n' >&2
    exit 0
  fi
  cat "${stderr_file}" >&2
  exit "${status}"

# Validate renovate.json with the Renovate config validator.
check_renovate_config:
  uv run --locked pre-commit run renovate-config-validator --files renovate.json
