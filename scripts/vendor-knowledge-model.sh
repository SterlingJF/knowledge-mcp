#!/usr/bin/env bash
# File: scripts/vendor-knowledge-model.sh
#
# Vendors the knowledge model from the public knowledge-bus repository at the given ref (default main).
# Local filenames use vault-starter convention (server/app/knowledge_model/loader.py).
set -euo pipefail
REF="${1:-main}"
BASE="https://raw.githubusercontent.com/SterlingJF/knowledge-bus/${REF}"
DEST="$(cd "$(dirname "$0")/.." && pwd)/knowledge-model"
curl -fsSL "${BASE}/spec/knowledge-bus-protocol.yaml"                        -o "${DEST}/Knowledge Bus Protocol (KBP).yaml"
curl -fsSL "${BASE}/universes/product-development/universe.kbp.yaml"         -o "${DEST}/Artifact Universe.kbp.yaml"
curl -fsSL "${BASE}/universes/product-development/type-guidance.kbp.yaml"    -o "${DEST}/Artifact Universe.type-guidance.kbp.yaml"
echo "vendored from SterlingJF/knowledge-bus@${REF}"
