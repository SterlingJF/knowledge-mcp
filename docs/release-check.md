# Release checks

See the [Release workflow](../.github/workflows/release.yml).
The `HOMEBREW_TAP_TOKEN` secret is a fine-grained token with read and write access to the tap repository's contents alone.

## Publish a release

1. Record user-visible changes under `## Unreleased` in `CHANGELOG.md`, grouped under Added, Changed, Removed and Fixed. Include upgrade steps for breaking changes.
2. Run `just release_prepare X.Y.Z` to update package versions, plugin versions, `uv.lock` and `runtime/requirements.lock`.
   The recipe renames `## Unreleased` to `## X.Y.Z` and stages nothing.
3. Run `just release_check`, then `just check`.
4. Commit, then push the tag `vX.Y.Z`. The tag version must match `runtime/pyproject.toml`.
5. Wait for the workflow to pass on both architectures.
   The workflow uploads bottles before checking installs and updates the tap after both install checks pass.
6. [Inspect the results](#inspect-the-results).

The workflow builds from the tagged commit and reads release notes from the tagged `CHANGELOG.md` entry.

## Add bottles to an existing release

1. Open Actions → Release → Run workflow. Enter the existing tag in the `tag` field.
   The tag version must match `runtime/pyproject.toml` at that tag.
2. Wait for the workflow to pass, then [inspect the results](#inspect-the-results).

The workflow reuses the published source archive and preserves the tag and release notes.
If the source archive is missing, the workflow builds an archive from the tag.
That build requires a `## X.Y.Z` entry in the tagged `CHANGELOG.md`.
Never move the tag or change the version or formula revision to add bottles.

A rerun reuses published bottles.
The workflow stops if either the bottle archive or its JSON metadata is missing from a published pair.
To recover, select Actions → Re-run failed jobs. The rerun publishes the retained build artifacts.

## Runners

| Runner           | Architecture | Bottle tag      | Homebrew prefix |
| ---------------- | ------------ | --------------- | --------------- |
| `macos-15`       | ARM64        | `arm64_sequoia` | `/opt/homebrew` |
| `macos-15-intel` | x86_64       | `sequoia`       | `/usr/local`    |

On each architecture, the verify job installs from source, then from the bottle, and checks:

- `poured_from_bottle` is `false` for the source install and `true` for the bottle install.
- `brew audit --strict`, `brew test`, `brew linkage --test` and `kb doctor` pass.
- The installed version matches the release.

## Inspect the results

Check the GitHub release for these assets:

| Asset          | Filename                                              |
| -------------- | ----------------------------------------------------- |
| Source         | `knowledge_mcp-<version>.tar.gz`                      |
| ARM64 metadata | `knowledge-mcp--<version>.arm64_sequoia.bottle.json`  |
| ARM64 bottle   | `knowledge-mcp-<version>.arm64_sequoia.bottle.tar.gz` |
| Intel metadata | `knowledge-mcp--<version>.sequoia.bottle.json`        |
| Intel bottle   | `knowledge-mcp-<version>.sequoia.bottle.tar.gz`       |

Check `SterlingJF/homebrew-tap/Formula/knowledge-mcp.rb` for the source URL and checksum, bottle root URL and both bottle checksums.
The tap job rejects downgrades.
For the same version, the tap job rejects changes to the source URL, source checksum or formula revision.

Check the Actions artifacts for the formula, release manifest, bottle builds and install reports.
Each `install-<bottle tag>` artifact contains `source-install.json`, `bottle-install.json`, and the install, test, linkage and doctor logs.
A failed run may have incomplete reports.
The `elapsed_seconds` field excludes dependency setup because the job installs dependencies before timing each install.

## Manual checks

Test each affected harness on an existing test installation. Run install and removal checks on a disposable test Mac.

### Installed package

```sh
brew install sterlingjf/tap/knowledge-mcp
brew test knowledge-mcp
brew audit --strict sterlingjf/tap/knowledge-mcp
brew info --json=v2 sterlingjf/tap/knowledge-mcp
kb --version
kb doctor
```

For a source install, replace the first command with `brew install --build-from-source sterlingjf/tap/knowledge-mcp`.
Check `brew info` for `poured_from_bottle: true` after a bottle install or `false` after a source install.

### Harnesses

1. Register knowledge-mcp with the [setup command](../README.md#get-started) for each harness under test, then start a new session.
2. Run `kb doctor`. Check the MCP server list in Claude Code, Codex, the Claude desktop app, Pi or OpenCode.
   Check that the knowledge-mcp entry runs `kb mcp` from the Homebrew path.
3. In a test codebase, pick an existing file and run `kb type <path>`.
   Ask the agent for the document type of the same file. Check that the agent calls `kb_get_document_type`.
4. In a harness with a skills folder, check that each `kb-*` skill appears once.
   The Claude desktop app takes skill uploads instead.

### Upgrade

After a newer version reaches the tap, run:

```sh
brew upgrade knowledge-mcp
brew test knowledge-mcp
brew audit --strict sterlingjf/tap/knowledge-mcp
brew info --json=v2 sterlingjf/tap/knowledge-mcp
kb doctor
```

Check that `kb doctor` shows the new version and `brew info` shows `poured_from_bottle: true`.
Check that skill links still use Homebrew's `opt/knowledge-mcp` path.

### Cleanup

1. Quit the harnesses under test.
2. Run `kb setup --remove <harness>` for each harness you registered for this check.
3. If you installed the package for this check, run `kb doctor --verbose` to find the state folder.
   Then run `brew uninstall knowledge-mcp`.

Uninstalling keeps the state folder. See [SECURITY.md](../SECURITY.md#known-limitations).
