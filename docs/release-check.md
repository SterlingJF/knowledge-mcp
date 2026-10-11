# Release check

Run this round on a Mac before announcing a release. It installs knowledge-mcp with Homebrew, sets it up in each agent app, asks about a file in each app, upgrades, and removes everything again. Each step lists the command and what it should show.

## Tag the release

The first release of knowledge-mcp with the `kb` command is tagged `v0.2.0`, because `v0.1.0` is already the tag of the earlier desktop app's release.

1. In `CHANGELOG.md`, replace `unreleased` in the heading of the `0.2.0` entry with the release date.
2. Push the tag `v0.2.0`. The release workflow refuses a tag that differs from the version in `runtime/pyproject.toml`, attaches the source archive to the GitHub release, installs and tests the formula, and pushes the formula to `SterlingJF/homebrew-tap`.
3. Wait for the workflow to finish. The tap's `Formula/knowledge-mcp.rb` then installs the `v0.2.0` source archive.

## Before you start

1. In System Settings, under Users & Groups, add a standard user for the check, such as `kbcheck`, and sign in to the new user once so macOS creates its home folder.
2. Homebrew lives in `/opt/homebrew` and belongs to your own user, so run the `brew` commands from your own account. Run every `kb` command, and every agent app, as `kbcheck`.
3. As `kbcheck`, put Homebrew's commands on PATH. A new user's shell reads only `/etc/paths`, which leaves out `/opt/homebrew/bin`, and the Homebrew installer adds `brew shellenv` to your own `~/.zprofile` alone:

   ```sh
   echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
   ```

   Then open a new terminal, so `kb` and the agent apps' command lines are found.

4. As `kbcheck`, install and sign in to Claude Code, Codex (the CLI, or the ChatGPT desktop app with its Codex mode), the Claude desktop app, Pi and OpenCode. Start each app once, then quit the app.

## Install

From your own account:

```sh
brew install sterlingjf/tap/knowledge-mcp
brew test knowledge-mcp
```

The install builds from source and ends with the caveats, which list `kb setup <host>` for each app, ask you to run `kb setup --remove <host>` before `brew uninstall`, and name the folder that keeps your answer log and edit record with the command that deletes the folder. `brew test` exits 0.

As `kbcheck`:

```sh
command -v kb
kb --version
kb doctor
```

`command -v kb` prints `/opt/homebrew/bin/kb`. `kb --version` shows `kb <version> (knowledge-bus <version>; universe specs and skills at v<version>)`, with the same knowledge-bus version in both places. `kb doctor` shows the knowledge-bus line, the kbp line, the bundled universe specs and skills, `KNOWLEDGE_MCP_STATE_DIR: not set`, `State folder: /Users/kbcheck/.local/state/knowledge-mcp`, and `not set up` for each app, then exits 0.

## Set up each app

As `kbcheck`:

```sh
kb setup claude-code
kb setup codex
kb setup claude-desktop
kb setup pi
kb setup opencode
```

| Command                   | It should show                                                                                                                                                                                                                                              |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `kb setup claude-code`    | `Registered knowledge-mcp with claude mcp add --scope user knowledge-mcp -- /opt/homebrew/opt/knowledge-mcp/bin/kb mcp.` (or `in ~/.claude.json` when `claude` is missing from PATH), then `Linked <n> skills into ~/.claude/skills`, one per bundled skill |
| `kb setup codex`          | `Registered knowledge-mcp in ~/.codex/config.toml: /opt/homebrew/opt/knowledge-mcp/bin/kb mcp.`, then the same skill links in `~/.agents/skills`; the entry's `env_vars` lists `KNOWLEDGE_MCP_STATE_DIR` and `XDG_STATE_HOME`                               |
| `kb setup claude-desktop` | `Registered knowledge-mcp in ~/Library/Application Support/Claude/claude_desktop_config.json`, then the line saying the app takes skills as uploads, with the folder to upload from                                                                         |
| `kb setup pi`             | the same through `pi mcp add`, then the same skill links in `~/.agents/skills`                                                                                                                                                                              |
| `kb setup opencode`       | `Registered knowledge-mcp in ~/.config/opencode/opencode.json`, the same skill links in `~/.agents/skills`, and one warning: OpenCode also reads `~/.claude/skills`, which holds the same skills for Claude Code                                            |

No other warning appears on a clean user. Then:

```sh
kb doctor
claude mcp list
codex mcp list
pi mcp list
opencode mcp list
```

`kb doctor` shows each app as registered, with one skill link per bundled skill for every app but the Claude desktop app, and exits 0. Each app's list shows `knowledge-mcp` running `/opt/homebrew/opt/knowledge-mcp/bin/kb mcp`, connected.

## Ask about a file in each app

As `kbcheck`, make a small codebase that holds no `.knowledge-bus/` folder:

```sh
mkdir -p ~/kb-check/docs/rfcs && cd ~/kb-check && git init -q
printf '# Cache\n' > docs/rfcs/0042-cache.md
kb fit docs/rfcs/0042-cache.md
```

`kb fit` prints JSON whose `universe_specs` list each bundled universe spec as a bundled copy at the tag `kb --version` shows, and whose `candidates` hold a design document type from each bundled universe spec that has one, matched on the folder.

Open each app in `~/kb-check` (for the Claude desktop app, a new chat) and ask:

> What is docs/rfcs/0042-cache.md for? The file is in ~/kb-check, which has no .knowledge-bus folder.

In each app, the agent calls `kb_fit` from knowledge-mcp, names the same candidates `kb fit` printed, and asks one question about whose work the file is, or states its guess and asks you to confirm. Answer "maintainer": the agent reads the card of the candidate kept for a codebase's maintainers with `kbp_card`.

Then check the skills in each app with a folder: in Claude Code, type `/kb-` and see each `kb-*` and `km-*` skill listed once; in Codex, Pi and OpenCode, open the skills list and see the same names.

## Upgrade

At the first release the tap holds no newer version, so run this section when the next release reaches the tap. From your own account:

```sh
brew upgrade knowledge-mcp
```

As `kbcheck`:

```sh
readlink ~/.agents/skills/kb-check
kb --version
kb doctor
```

`readlink` still shows `/opt/homebrew/opt/knowledge-mcp/libexec/lib/python3.14/site-packages/knowledge_mcp/skills/kb-check`, which now holds the new version's skill. `kb --version` shows the new version, and `kb doctor` exits 0. When a new version adds a skill, `kb doctor` names the missing link and the two commands that add the link.

## Remove

As `kbcheck`, quit every agent app, so no session starts the server again. Then:

```sh
kb setup --remove claude-code
kb setup --remove codex
kb setup --remove claude-desktop
kb setup --remove pi
kb setup --remove opencode
kb doctor
```

Each removal ends with `<app> no longer starts knowledge-mcp`. The first four removals print nothing about the state folder. The last removal adds two lines, which name the variable and the folder holding the answers and edits the apps recorded during the check:

```text
KNOWLEDGE_MCP_STATE_DIR: not set
Your answer log, edit record and any Explorer folders stay in /Users/kbcheck/.local/state/knowledge-mcp.
```

`kb doctor` shows `not set up` for each app. Then check that everything setup installed is gone and the state folder remains:

```sh
grep -ls knowledge-mcp ~/.claude.json ~/.codex/config.toml ~/.pi/agent/mcp.json \
  ~/.config/opencode/opencode.json "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
find ~ -lname '*knowledge-mcp*' 2>/dev/null
ls ~/.local/state/knowledge-mcp
```

`grep` and `find` print nothing. `ls` lists `log.jsonl` and any other history the apps recorded, and no `setup` folder.

From your own account:

```sh
brew uninstall knowledge-mcp
brew untap sterlingjf/tap
```

`which kb` as `kbcheck` prints nothing, and `ls ~/.local/state/knowledge-mcp` still lists `log.jsonl`. Remove the `kbcheck` user in System Settings when you are done.
