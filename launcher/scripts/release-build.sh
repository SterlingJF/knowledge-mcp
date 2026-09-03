#!/usr/bin/env bash
# File: launcher/scripts/release-build.sh
#
#
# Setup, once per release machine: an Apple Developer Program membership, a "Developer ID
# Application" certificate in the login keychain, and stored notary credentials:
#   xcrun notarytool store-credentials knowledge-mcp --apple-id <email> --team-id <TEAMID>

set -euo pipefail

LAUNCHER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="${KM_NOTARY_PROFILE:-knowledge-mcp}"

signing_identity() {
  security find-identity -v -p codesigning \
    | grep 'Developer ID Application' | head -1 | sed -E 's/.*"(.+)"/\1/'
}

require_credentials() {
  IDENTITY="$(signing_identity || true)"
  if [[ -z "${IDENTITY}" ]]; then
    echo "ERROR: no 'Developer ID Application' certificate in the keychain." >&2
    echo "       See the setup notes at the top of this script." >&2
    exit 2
  fi
  if ! xcrun notarytool history --keychain-profile "${PROFILE}" >/dev/null 2>&1; then
    echo "ERROR: no notary credentials stored under profile '${PROFILE}'." >&2
    echo "       See the setup notes at the top of this script." >&2
    exit 2
  fi
  TEAM_ID="$(sed -E 's/.*\(([A-Z0-9]+)\)$/\1/' <<<"${IDENTITY}")"
}

build() {
  bash scripts/build-sidecars.sh
  # Tauri signs app and sidecars with hardened runtime and tauri.conf.json entitlements.
  APPLE_SIGNING_IDENTITY="${IDENTITY}" APPLE_TEAM_ID="${TEAM_ID}" \
    pnpm exec tauri build --bundles app,dmg
  DMG="$(ls "${LAUNCHER_DIR}"/src-tauri/target/release/bundle/dmg/*.dmg | head -1)"
}

notarize() {
  echo ">>> Notarizing (Apple's queue; typically 1-15 minutes)"
  xcrun notarytool submit "${DMG}" --keychain-profile "${PROFILE}" --wait
  xcrun stapler staple "${DMG}"
}

verify() {
  spctl --assess --type open --context context:primary-signature -v "${DMG}"
  xcrun stapler validate "${DMG}"
}

main() {
  require_credentials
  echo ">>> Signing as: ${IDENTITY}"
  cd "${LAUNCHER_DIR}"
  build
  notarize
  verify
  echo ">>> Release artifact: ${DMG}"
}

main
