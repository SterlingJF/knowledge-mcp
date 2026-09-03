#!/usr/bin/env bash
# File: launcher/scripts/build-sidecars.sh
#
# Run before first Rust build. Tauri resolves external binaries at compile time.
# Tauri expects `<name>-<target triple>` filenames.

set -euo pipefail

LAUNCHER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$(cd "${LAUNCHER_DIR}/.." && pwd)"
BACKEND_DIR="${REPO_DIR}/server"
MCP_DIR="${REPO_DIR}/mcp"
KNOWLEDGE_MODEL_DIR="${REPO_DIR}/knowledge-model"
OUTPUT_DIR="${LAUNCHER_DIR}/src-tauri/binaries"

# Homebrew rustup may be absent from PATH. rustc supplies target triple.
if ! command -v rustc >/dev/null 2>&1 && [[ -d /opt/homebrew/opt/rustup/bin ]]; then
  export PATH="/opt/homebrew/opt/rustup/bin:${PATH}"
fi

command -v rustc >/dev/null 2>&1 || {
  echo "ERROR: rustc is not on PATH, so the target triple cannot be resolved." >&2
  exit 2
}

TRIPLE="$(rustc --print host-tuple)"

mkdir -p "${OUTPUT_DIR}"

echo ">>> Freezing the backend"
echo "    Source:    ${BACKEND_DIR}"
echo "    Universes: ${KNOWLEDGE_MODEL_DIR}"
echo ""

cd "${BACKEND_DIR}"

# Absolute: PyInstaller resolves --add-data against --specpath.
uv run --group build pyinstaller \
  --noconfirm --clean --onefile --noupx --target-arch arm64 \
  --name km-server \
  --distpath "${BACKEND_DIR}/dist" \
  --workpath "${BACKEND_DIR}/build" \
  --specpath "${BACKEND_DIR}/build" \
  --add-data "${KNOWLEDGE_MODEL_DIR}:knowledge-model" \
  --collect-submodules uvicorn \
  app/entrypoints/desktop.py

cp "${BACKEND_DIR}/dist/km-server" "${OUTPUT_DIR}/km-server-${TRIPLE}"
chmod +x "${OUTPUT_DIR}/km-server-${TRIPLE}"

echo ""
echo ">>> Freezing the model-context server"
echo "    Source: ${MCP_DIR}"
echo ""

cd "${MCP_DIR}"

uv run --group build pyinstaller \
  --noconfirm --clean --onefile --noupx --target-arch arm64 \
  --name km-mcp \
  --distpath "${MCP_DIR}/dist" \
  --workpath "${MCP_DIR}/build" \
  --specpath "${MCP_DIR}/build" \
  --collect-submodules mcp.server \
  --collect-submodules mcp.shared \
  --collect-submodules mcp.types \
  --collect-submodules mcp.os \
  --collect-submodules uvicorn \
  --collect-submodules httpx \
  --exclude-module mcp.cli \
  --exclude-module typer \
  app/entrypoints/local.py

cp "${MCP_DIR}/dist/km-mcp" "${OUTPUT_DIR}/km-mcp-${TRIPLE}"
chmod +x "${OUTPUT_DIR}/km-mcp-${TRIPLE}"

echo ""
echo ">>> Frozen"
for binary in "${OUTPUT_DIR}/km-server-${TRIPLE}" "${OUTPUT_DIR}/km-mcp-${TRIPLE}"; do
  file "${binary}"
  codesign -dv "${binary}" 2>&1 | grep -E 'Signature|Identifier' || true
done
