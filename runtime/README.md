# Runtime

This package contains the knowledge-mcp server, the `kb` command and the bundled writing skills. Read the [project README](https://github.com/SterlingJF/knowledge-mcp#readme) for installation and use. Use the layout and commands below to maintain the package. [UPSTREAM.md](knowledge-bus/UPSTREAM.md) records the copied upstream material and pinned release.

## Layout

```text
runtime/
├── README.md
├── pyproject.toml                   package knowledge-mcp, command kb, knowledge-bus pin; ships knowledge-bus/ and skills/ in the package
├── requirements.lock                hashed export of uv.lock; the installed plugin runs from it
├── .claude-plugin/plugin.json       Claude Code manifest; declares the stdio server
├── .codex-plugin/plugin.json        Codex manifest
├── codex-mcp.json                   Codex's stdio server declaration
├── .gitignore
├── knowledge_mcp/
│   ├── cli.py                       kb: mcp, setup, fit, kbp, doctor, --version
│   ├── main.py                      build_server() and the stdio server
│   ├── __main__.py                  python -m knowledge_mcp: the stdio server
│   ├── hosts.py                     each agent app's settings file, skills folder and command line
│   ├── setup.py                     kb setup, kb setup --remove and kb doctor, with their state file
│   ├── configedit.py                adds and removes one entry in a JSON or TOML settings file
│   ├── localfit.py                  kb fit: reads a local file's folder chain and calls kb_fit
│   ├── start.py                     both manifests start this: builds the hash-checked environment, then runs knowledge_mcp
│   ├── contract.py                  what a host sends: folders and universe specs in scope
│   ├── scope.py                     rebuilds those folders in a private temporary folder
│   ├── bundled.py                   the bundled universe specs and skills, and their ref
│   ├── kbp.py                       runs the installed kbp console script
│   ├── fit.py                       matches a file name and folder against document types
│   ├── audience.py                  reads the audience frame from kbp --inspect output
│   ├── edits.py                     the edit record, in the state folder
│   ├── record.py                    the fit record: reads, merges and returns its text
│   ├── mark.py                      reads element questions from kbp --card output, for kb_mark
│   ├── passages.py                  splits an outside document's text into passages
│   ├── log.py                       one JSON Lines entry per answer, in the state folder
│   └── tools/                       kb_fit, kb_audience, the edit record tools, kb_fit_record, kb_mark, one tool per kbp mode
├── knowledge-bus/                   copied by `just refresh_knowledge_model` (never edit)
│   ├── UPSTREAM.md                  ref, date, and SHA-256 of every copied file
│   └── universes/<id>/              the bundled universe specs
├── skills/kb-*/                     knowledge-bus's skills, copied as is (never edit)
├── skills/km-write/SKILL.md         knowledge-mcp's own skill: the checks before writing
├── skills/km-fit-record/SKILL.md    knowledge-mcp's own skill: keeping the fit record
├── skills/km-bring-in/SKILL.md      knowledge-mcp's own skill: bringing in an outside document
├── scripts/generate_tools_doc.py    writes or checks the intro and the tool tables in a tools doc
└── tests/
    ├── hosts.py                     knowledge-base fixtures and what a host sends for them
    ├── record_host.py               a knowledge base, local or content only, and a host keeping its fit record
    ├── test_fit_end_to_end.py       kb_fit through the stdio server
    ├── test_kb_end_to_end.py        kb setup and --remove for every host, kb fit, kb mcp, kb kbp, kb doctor, the built package
    ├── test_configedit.py           one entry in and out of JSON and TOML settings, byte for byte
    ├── test_audience.py             kb_audience on both bundled universe specs
    ├── test_edits.py                recording, listing and undoing an edit
    ├── test_fit_record_end_to_end.py  the fit record across sessions and simultaneous chats
    ├── test_fit_record.py           the fit record's merge rules
    ├── test_mark_end_to_end.py      kb_mark on a pasted chat thread and a document at a Drive link
    ├── test_passages.py             passage boundaries
    ├── test_tools.py                the tool list: nothing commits, pushes or posts
    ├── test_kbp_tools.py            each kbp tool against kbp run directly
    ├── test_log.py
    ├── test_plugin.py               the folder copied alone, started from each manifest
    ├── test_fit.py
    └── test_scope.py
```

## Commands

| Command                                                      | Purpose                                                                                                 |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------- |
| `uv run --locked kb mcp`                                     | Start the stdio server                                                                                  |
| `uv run --locked kb <command>`                               | Run any `kb` command from this folder                                                                   |
| `uv run --locked pytest`                                     | Run the tests                                                                                           |
| `uv run --locked python scripts/generate_tools_doc.py <doc>` | Write the intro and the tool tables in `<doc>`; `--check` fails on a stale doc                          |
| `just check_runtime`                                         | From the repo root: check the tools doc and the lock, then lint, format-check, and test                 |
| `just generate_knowledge_mcp_lock`                           | From the repo root: write `requirements.lock` from `uv.lock`                                            |
| `just refresh_knowledge_model <tag>`                         | From the repo root: copy knowledge-bus's universe specs and skills at `<tag>`, the pinned release's tag |
| `just generate_mcp_tools_doc`                                | From the repo root: write the intro and the tool tables in `docs/mcp-tools.md`                          |

To move knowledge-bus to a new release, point the pin in `pyproject.toml` at the release's source archive, `https://github.com/SterlingJF/knowledge-bus/releases/download/<tag>/knowledge_bus-<version>.tar.gz`, run `uv lock` and `just generate_knowledge_mcp_lock`, check the hash in `uv.lock` against the release's `SHA256SUMS`, then run `just refresh_knowledge_model <tag>`.
