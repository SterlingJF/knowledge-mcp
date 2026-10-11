# MCP tools

<!-- BEGIN AUTO-GENERATED intro -->

The server has 14 tools. It speaks MCP over stdio: each agent app starts the server with `kb mcp` or from its plugin, and the server opens no network port.

<!-- END AUTO-GENERATED intro -->

> The intro and the tool tables are generated from [source](../runtime/knowledge_mcp/tools) by `just generate_mcp_tools_doc`.

## Fit a file

| Tool     | What it does                                                                      |
| -------- | --------------------------------------------------------------------------------- |
| `kb_fit` | Say what a file is for: every fitting universe spec and document type, as a list. |

`kb_fit` takes what the agent read about one file and answers with every universe spec and document type that fits it, as a list. The agent sends:

| Argument         | What it holds                                                                                                                                                                                                                                                                 |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `location`       | The file's location as plain text: a local path, a Drive link or a Notion page. knowledge-mcp logs the text and opens nothing there.                                                                                                                                          |
| `name`           | The file name.                                                                                                                                                                                                                                                                |
| `folders`        | Folder names from the knowledge base's top folder down to the file's folder.                                                                                                                                                                                                  |
| `universe_specs` | One entry per folder on that chain holding a `.knowledge-bus/`, empty ones included: its `depth` in `folders`, the name and header id and version of each `*.kbp.yaml` file directly inside, and the text of `workspace.yaml` when present. Nothing under `plugins/` goes in. |
| `hat`            | The role of the person the agent works for, when the agent can tell.                                                                                                                                                                                                          |
| `record`         | The text of the knowledge base's fit record, `.knowledge-bus/plugins/knowledge-mcp/record.yaml`, when it has one; `record_digest` in its place once an answer returned the digest.                                                                                            |
| `changes`        | Files moved or deleted since the record was saved, in the shape `kb_fit_record` takes, sent with the record. knowledge-mcp applies them to the record for this answer and saves nothing.                                                                                      |

For a header whose id and version match a bundled universe spec, the agent sends the header alone: knowledge-mcp uses its bundled copy and labels the answer `bundled copy at <ref>`. Any other file's text is sent once per session; the answer returns its digest, which later calls send instead. When no folder on the chain holds a `*.kbp.yaml` file or `workspace.yaml`, the bundled universe specs apply, so a `.knowledge-bus/` holding only the fit record changes nothing. When a farther folder holds definitions and a nearer `.knowledge-bus/` holds none, `kbp` refuses the scope, and knowledge-mcp passes the refusal through as is.

knowledge-mcp rebuilds those folders at their places in a private temporary folder, runs `kbp --kinds` from the file's rebuilt folder, and matches the file name and the folder holding it against each document type's other names. The answer lists the candidates with their `kbp --kinds` fields, matching actors first when a hat is sent. With no candidate, it lists every document type in scope instead, for the agent to choose from the file's outline or to answer "no fit". When the agent sends the fit record and the record holds the file, with its universe spec still in scope, the answer comes from the record: `recorded` holds the entry, labelled "from the record", including "no fit", and the candidates are empty. The result schema is [`fit.schema.yaml`](../contracts/project/v1/fit.schema.yaml).

## Before writing

| Tool             | What it does                                                                                                   |
| ---------------- | -------------------------------------------------------------------------------------------------------------- |
| `kb_audience`    | Return who a document of one type can be for, from the document type's own universe spec.                      |
| `kb_record_edit` | Record an edit you made to a document, right after making the edit, so the person can check and undo the edit. |
| `kb_edits`       | List every edit recorded at a location, oldest first, with its basis and its texts.                            |

Before writing or editing a document, the agent follows the plugin's `km-write` skill. It settles the fit with `kb_fit`, reads the card with `kbp_card`, and states each condition on the card's "Depends on: …" lines as a guess labelled "guess", which stays open until the person confirms the value. When the guesses meet the card's "No document needed when …" line, the agent answers with the label "no document needed (guess)" and asks whether to write the document anyway. The agent keeps that answer apart from "no fit".

`kb_audience` takes the same `location`, `folders` and `universe_specs` as `kb_fit`, plus the document type id in `kind` and, when several universe specs in scope hold that id, the universe spec in `universe`. knowledge-mcp runs `kbp --kinds` to find the universe spec and the document type's `actor`, then `kbp --inspect` on that universe spec. When the universe spec declares an `audience` frame, `choices` lists the frame's values in the universe spec's order; otherwise `choices` is empty and the agent writes for the `actor`. The result schema is [`audience.schema.yaml`](../contracts/project/v1/audience.schema.yaml).

The agent edits only when the person asked in that session, when a standing line the person wrote covers the edit, or for a change row the person accepted. After each edit it calls `kb_record_edit`:

| Argument         | What it holds                                                                            |
| ---------------- | ---------------------------------------------------------------------------------------- |
| `location`       | The document's location as plain text.                                                   |
| `basis`          | `request`, `line` or `change_row`.                                                       |
| `basis_text`     | The request, the standing line or the change row, quoted.                                |
| `basis_location` | The file or place holding the line or change row, such as `AGENTS.md`.                   |
| `before`         | The text the edit replaced, the whole file or the passage; empty for a new file.         |
| `after`          | The text that replaced `before`.                                                         |
| `whole_file`     | True when `before` is the whole file. Only then can `after_digest` stand in for `after`. |

`after_digest` is `sha256:` and the 64 lowercase hex digits of the SHA-256 of `after`. A passage needs its `after` text, so the agent can find the passage again to undo the edit. knowledge-mcp appends each record to `edits.jsonl` in its state folder and returns the record's id and the digests of both texts. `kb_edits` lists every record for a location, oldest first, with its texts. To undo an edit, the agent checks that the document still holds the `after` text and puts the `before` text back. No tool commits, pushes, opens issues or pull requests, or posts comments.

## Keep the fit record

| Tool            | What it does                                                                                                                                                                                          |
| --------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `kb_fit_record` | Keep the fit record, `.knowledge-bus/plugins/knowledge-mcp/record.yaml` in the knowledge base's top folder: which universe spec and document type each file is, or "no fit", and who the file is for. |

The fit record is `.knowledge-bus/plugins/knowledge-mcp/record.yaml` at the knowledge base's top folder: knowledge-mcp keeps its file in a plugin folder of its own inside `.knowledge-bus/`, and the host creates the folders when missing. `kbp` reads only the definitions directly inside `.knowledge-bus/`, so the record changes no universe spec in scope. The record holds one entry per file, keyed by the file's path from the top folder: the universe spec id and version and the document type id, or `no_fit: true`; who the document is for, with `confirmed` or `guessed`, when known; `made`, `fit` when the agent settled the fit or `correction` when the person stated the fit; `allowed_by`, the request, standing line or accepted change row that allowed the save; a fingerprint when the host sent one; and the time. The file's schema is [`fit-record.schema.yaml`](../contracts/project/v1/fit-record.schema.yaml).

The host reads and writes the record; knowledge-mcp merges. The agent sends `kb_fit_record`:

| Argument                                | What it holds                                                                                                                                                                                        |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `location`                              | The knowledge base's location as plain text.                                                                                                                                                         |
| `record` or `record_digest`             | The record's text as read just now, an empty text when the file is missing, or the digest an earlier answer in the session returned.                                                                 |
| `universe_specs`                        | Every folder holding a `.knowledge-bus/`, by its path from the top folder, with the same files and `workspace.yaml` as `kb_fit` takes, and nothing under `plugins/`.                                 |
| `listing`                               | Every file of the knowledge base outside `.knowledge-bus/`, each with an optional fingerprint, on a session's first call.                                                                            |
| `changes`                               | Files `created`, `deleted`, `moved` (with `old_path`) or `edited` (with the new fingerprint), as an editor reports changes.                                                                          |
| `fits`                                  | Each file's fit: `made` `fit` for a fit the agent settled, `correction` for a fit or reader the person stated; a universe spec and document type, `no_fit`, or `audience` alone for a recorded file. |
| `refit`                                 | True to list every recorded file for settling again, corrections excepted.                                                                                                                           |
| `basis`, `basis_text`, `basis_location` | The ground for saving: a request in the session, a standing line the person wrote, or an accepted change row.                                                                                        |

knowledge-mcp compares a listing with the record. A missing file and a new file with the same fingerprint make one move, and so do a missing file and a new file sharing a file name no other such file has, unless the two carry different fingerprints. Every other missing file is deleted, and every other new file is created. The answer lists these changes in `listing_changes`, in the shape `changes` takes. A deleted entry that held a correction or a confirmed reader comes back with a note, so the agent can ask the person whether the file moved. A moved file keeps a correction or a confirmed reader when its universe spec is in scope at the new path; a moved plain fit, like a new file, waits in `to_settle` with its candidates, as `kb_fit` gives them, and with the entry it had in `was`. Each scope's universe specs, and every document type in scope when a file matched none on its name, come once in `scopes`. For a file the person corrected, knowledge-mcp keeps the correction and lists the agent's fit as `kept`.

The answer lists the `changed` entries and returns the merged `record` text with its `digest`, or `record` null when nothing changed or no ground came with the call. Right before writing, the host reads the file again: when the file still holds the text sent, the host writes the returned text; when another chat saved meanwhile, the host sends the new text with the same changes and fits, and writes the text of the second answer. When the call that merges again is the call that carried the listing, the host adds that answer's `listing_changes` to `changes` in place of the listing. Compared with the newer text, the earlier listing would drop the other chat's new files and bring back the files the other chat deleted. No chat loses the other's entries. The result schema is [`fit-record-update.schema.yaml`](../contracts/project/v1/fit-record-update.schema.yaml).

## Bring in a document

| Tool      | What it does                                                                                                                     |
| --------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `kb_mark` | Split an outside document's text into passages, and return the passages with the element questions to mark each passage against. |

To bring in a document written elsewhere, such as a pasted chat thread, a Drive file or a Notion page, the agent follows the plugin's `km-bring-in` skill. It reads the document through its own tools or a connector and sends `kb_mark`:

| Argument         | What it holds                                                                                                                                                |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `location`       | The document's location, as plain text: a local path, a Drive link, a Notion page, or `pasted in chat`.                                                      |
| `text`           | The document's text.                                                                                                                                         |
| `folders`        | Folder names from the knowledge base's top folder down to the folder the document comes into; empty for the top folder, and when the person named no folder. |
| `universe_specs` | The `.knowledge-bus/` folders on that chain, in the shape `kb_fit` takes. With none, the bundled universe specs apply.                                       |

knowledge-mcp rebuilds the folders, runs `kbp --kinds`, then `kbp --card <kind> --universe <id> --format json` for every document type in scope, and keeps each card's sections that the document type keeps. knowledge-mcp skips a section the card links to another document type, and lists the element under that document type, from that document type's own card. The cards for a scope stay in memory for the session, so a second document coming into the same folder gets its answer at once. The answer lists each universe spec in scope with its source label, each document type with its name, `action` and `actor`, and each element with its id, question and strength, in the card's order.

knowledge-mcp also splits the text into passages: each heading, list item and fenced code block, and each run of other lines between blank lines. Each passage has an id such as `p3`, its first and last line counting from 1, its opening words, and the id of the heading above the passage. knowledge-mcp splits by layout alone and judges nothing a passage says, so an instruction inside the document comes back as a passage like any other. A text holding no passage gets a refusal. The result schema is [`mark.schema.yaml`](../contracts/project/v1/mark.schema.yaml).

The agent marks each passage `settles`, `answers in part` or `contradicts` with the universe spec, document type and element, or `fits nowhere`. It shows the marks and the edited text of each target note, files only on the person's yes or under a standing line the person wrote, and records each edit with `kb_record_edit`. No decision model runs: the agent marks the passages.

## From the terminal

`kb fit <file>` makes the terminal the host. It finds the knowledge base's top folder, the highest folder above the file that holds a `.knowledge-bus/` (or the folder named with `--top`), and reads what an agent would send: the file's name, its path as the location, its folders, every `.knowledge-bus/` on the folder chain with each `*.kbp.yaml` header, the text of any file that matches no bundled universe spec, `workspace.yaml`, and the fit record's text when the top folder holds one. It never reads the file itself. Then it calls `kb_fit` in its own process and prints the answer, the same JSON an agent gets. `--hat` sends the hat. A refusal exits with code 1.

## knowledge-bus

| Tool             | What it does                                                                                                                                                    |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `kbp_check`      | Check the universe specs in scope against the knowledge-bus protocol and return kbp's report as is.                                                             |
| `kbp_self_check` | Check the bundled knowledge-bus protocol against itself and return the `kbp --self-check` report as is.                                                         |
| `kbp_version`    | Return the knowledge-bus release and protocol version that `kbp --version` prints.                                                                              |
| `kbp_mint`       | Mint codes that collide with no code in the universe specs in scope, as `kbp --mint <kind> <count>` prints the codes.                                           |
| `kbp_inspect`    | Return the JSON model `kbp --inspect` builds for a universe spec in scope and its guidance.                                                                     |
| `kbp_explore`    | Write the offline Explorer for a universe spec in scope into knowledge-mcp's private folder, and return kbp's receipt and the folder's path.                    |
| `kbp_kinds`      | List every document type in scope as `kbp --kinds` prints the list: `kinds/1` for one universe spec, `kinds-set/1` for several.                                 |
| `kbp_card`       | Return the card for one document type as `kbp --card <kind> --format markdown` prints the card: sections, guidance, conditions and their "Depends on: …" lines. |

Each `kbp_*` tool runs the installed `kbp` console script and returns its stdout and stderr as is, each in its own block, with the exit code in the result's `_meta.exit_code`. A non-zero exit marks the result as an error. A last block, when present, says which files came from the bundled copies and gives the digests of text received.

The tools that read universe specs take the same `location`, `folders` and `universe_specs` as `kb_fit`, and `kbp` runs from the rebuilt folder with no target. `kbp_check` runs only on text the agent sent, never on a bundled copy. `kbp_explore` writes into knowledge-mcp's state folder and names the folder in its last block.

## The log

Every answer adds one line to `log.jsonl` in knowledge-mcp's state folder: `$KNOWLEDGE_MCP_STATE_DIR` when set, else `$XDG_STATE_HOME/knowledge-mcp`, else `~/.local/state/knowledge-mcp`. Each line holds the time, the tool, the location text, a SHA-256 digest of the arguments and every text returned. The edit record, `edits.jsonl`, sits in the same folder, so each edit can be checked against the answers the agent had when it wrote. knowledge-mcp writes no fit record: the host saves the text `kb_fit_record` returns, and the log keeps each of those answers. For `kb_mark`, the log keeps a digest of the arguments, the document's text included, and each passage's opening words.
