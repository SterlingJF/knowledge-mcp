# Vault Structure

## The six folders

| Folder           | What it holds                                                                     |
| ---------------- | --------------------------------------------------------------------------------- |
| `+`              | Capture and conventions — what enters the vault before it has a home.             |
| `Atlas`          | Knowledge that isn't bound to time — the space of ideas and assets.               |
| `Calendar`       | Moments in time — daily notes, meeting notes.                                     |
| `Efforts`        | Time-bound work — projects that open, evolve, and close.                          |
| `x`              | Everything outside the other three — files, media, raw source content, templates. |
| `.knowledge-mcp` | The vault's own configuration. Created empty today; reserved.                     |

## Becoming a vault

Creating a vault initializes all six folders. Opening an existing folder creates the absent ones
and adopts the rest — **anything else at the top level is left alone**. Nothing is moved, renamed,
or deleted; a folder full of loose files becomes a vault without a single existing file changing.

Each vault gets a minted id — sixteen hex characters, generated once, never derived from the
path — so renaming or moving the folder never orphans it. The registry lives at
`~/.config/knowledge-mcp/config.json`.

## What Knowledge-MCP sees

Knowledge-MCP can see every file under `+`, `x`, `Atlas`, `Calendar`, and `Efforts`, however deeply
nested. If a file or folder appears there in Finder — including through a symlink — it is part of
the vault.

Dot-folders, common working directories (e.g. `node_modules`, `.git`), and loose files at the vault root are ignored.`.knowledge-mcp` is considered internal (also ignored).

Markdown is read directly. Other files are exposed to agents by their local path.

## The bare-name caveat

The declared names are bare (`Atlas`, not `Atlas (general notes)`). Opening a vault that uses
decorated names adopts what matches and creates bare folders beside what doesn't. Nothing is
lost, but the two families coexist until folder mapping ships.
