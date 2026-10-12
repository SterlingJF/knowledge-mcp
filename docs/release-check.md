# Release verification

Publishing uses the GitHub release workflow. The workflow runs the native Homebrew checks on macOS runners.

## Publish a release

1. Write the changes under `## X.Y.Z — unreleased` in `CHANGELOG.md`.
2. Run `just release_prepare X.Y.Z`. Preparation updates package and plugin versions and lockfiles, then promotes that changelog heading. The changes remain unstaged.
3. Run `just release_check` to check release metadata and notes, then `just check` for the repository's normal code, format and test checks.
4. Commit the prepared changes, then push a stable tag `vX.Y.Z` matching `runtime/pyproject.toml`. The workflow builds from that tag and its lockfiles and uses its changelog entry for release notes.
5. Wait for the workflow to finish. The tap updates only after both architectures pass all required checks. Bottle assets are uploaded before install verification; an uploaded asset alone does not mean the release passed.
6. Inspect the release assets and tap formula as described below.

## Add bottles to an existing release

Open Actions → Release → Run workflow and enter the existing stable release tag in the `tag` input. The tag must match the package version in the tagged `runtime/pyproject.toml`. The workflow reuses an existing source archive and its tagged lockfiles without rewriting the tag or release notes. A release without that archive must pass the tagged metadata and changelog checks before the workflow creates or uploads its source archive. Do not move the tag or change the package version or formula revision to add bottles. Wait for the checks and inspect the results before marking the backfill complete.

Retries reuse published native bottle JSON and archives without replacing either. If a published pair is incomplete, use Actions → Re-run failed jobs to finish publication from the original retained build artifacts. A new run refuses to rebuild an incomplete pair.

## Automated Homebrew checks

The workflow uses these native runners:

| Runner           | Architecture | Bottle tag      | Homebrew prefix |
| ---------------- | ------------ | --------------- | --------------- |
| `macos-15`       | ARM64        | `arm64_sequoia` | `/opt/homebrew` |
| `macos-15-intel` | x86_64       | `sequoia`       | `/usr/local`    |

As of October 2026, macOS 15 is [Homebrew's oldest supported Apple Silicon OS](https://docs.brew.sh/Support-Tiers); Intel macOS is Tier 3. Recheck [GitHub's runner availability](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) before changing the baseline.

Each architecture builds or restores its native bottle. Verification runs on a fresh macOS runner and checks:

- An ordinary install has `poured_from_bottle: true`; a forced source install has `poured_from_bottle: false`.
- `brew test`, `brew audit --strict`, linkage checks and `kb doctor` succeed.
- The installed version matches the release.

These jobs provide the clean-install check when the workflow runs. Running `just check` locally tests tooling with fixtures and dry runs; it does not establish a native bottle install result.

The application bottle includes its compiled Rust Python extensions. Homebrew runtime dependencies such as Python and OpenSSL may still compile on Intel.

## Inspect the results

Check that the GitHub release contains the source archive and both native JSON/archive pairs:

| Asset          | Filename                                              |
| -------------- | ----------------------------------------------------- |
| Source         | `knowledge_mcp-<version>.tar.gz`                      |
| ARM64 metadata | `knowledge-mcp--<version>.arm64_sequoia.bottle.json`  |
| ARM64 bottle   | `knowledge-mcp-<version>.arm64_sequoia.bottle.tar.gz` |
| Intel metadata | `knowledge-mcp--<version>.sequoia.bottle.json`        |
| Intel bottle   | `knowledge-mcp-<version>.sequoia.bottle.tar.gz`       |

Check that `SterlingJF/homebrew-tap/Formula/knowledge-mcp.rb` uses the release's source URL and checksum, bottle root URL and both bottle checksums. A same-version update must preserve the existing source URL, source checksum and formula revision. An older backfill cannot downgrade the tap.

For a successful run, Actions retains the formula and release manifest, the original bottle build artifacts, and install reports. Each architecture's reports include `source-install.json`, `bottle-install.json` and separate install, test, linkage and doctor logs. A failed verification may retain only partial reports or logs. Use the recorded times rather than assuming a speedup.

The timed installs have runtime and build dependencies preinstalled, with Knowledge-MCP's downloads cleared before each install. They exclude cold dependency setup and do not measure a fresh machine's total install time.

## Manual app verification

Use an existing test installation to check affected agent apps. Run package installation and removal checks on a disposable test Mac. These manual checks are separate from routine publishing.

### Check the installed package

To check source installation, use `brew install --build-from-source sterlingjf/tap/knowledge-mcp` instead of the first install command below.

```sh
brew install sterlingjf/tap/knowledge-mcp
brew test knowledge-mcp
brew audit --strict sterlingjf/tap/knowledge-mcp
brew info --json=v2 sterlingjf/tap/knowledge-mcp
kb --version
kb doctor
```

For a bottle install, the receipt has `poured_from_bottle: true`; for a source install, it has `poured_from_bottle: false`. `brew test` checks the CLI versions and MCP initialization. `kb doctor` reports the installed components, app registration status and state folder.

### Check the agent apps

For changes to setup behavior, use the affected app's [setup command from the README](../README.md#get-started) to register or update Knowledge-MCP. Start a new session after setup.

Run `kb doctor` and check the app's MCP status. The CLI apps provide `claude mcp list`, `codex mcp list`, `pi mcp list` or `opencode mcp list`. The connection should run `kb mcp` through the installed Homebrew path.

Choose an existing file in a test codebase. Compare `kb fit <file>` with the agent's answer when asked what that file is for. The agent should call `kb_fit`, show the matching candidates and ask one question about the intended reader or ask you to confirm its guess. For a codebase without a `.knowledge-bus/` folder, the results use the bundled universe specs.

In an app that supports a skills folder, check that the bundled `kb-*` and `km-*` skills appear once. Claude Code provides the `/kb-` list; Codex, Pi and OpenCode provide skills lists. The Claude desktop app uses skill uploads instead.

### Check an upgrade

After a newer version reaches the tap, run `brew upgrade knowledge-mcp`, `brew test knowledge-mcp`, `brew audit --strict sterlingjf/tap/knowledge-mcp`, `brew info --json=v2 sterlingjf/tap/knowledge-mcp` and `kb doctor`. Check the new version and the `poured_from_bottle: true` receipt. Skill links should still point through Homebrew's `opt/knowledge-mcp` path. Keep this check pending until a newer version is available.

### Remove the test integration

Quit the apps under test. Use `kb setup --remove <host>` only for integrations added during this check. Uninstall the package with `brew uninstall knowledge-mcp` only if it was installed for this check.

Uninstalling retains the answer log and edit record. While the package is installed, `kb doctor` shows the state folder in use.
