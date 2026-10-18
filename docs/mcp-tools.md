# MCP tools

<!-- BEGIN AUTO-GENERATED intro -->

The server serves MCP over stdio and opens no network port. Harnesses with a knowledge-mcp plugin start the server through the plugin. Other harnesses run `kb mcp`.

<!-- END AUTO-GENERATED intro -->

> Generated regions come from [tools.json](../contracts/extensions/mcp/v1/tools.json), the `tools/list` response. After a tool change, run `just generate_contract_snapshots`, then `just generate_mcp_tools_doc`.

## Tools

<!-- BEGIN AUTO-GENERATED tools -->

| Tool                           | Purpose                                                                                                                                                       | Result                                                                                                |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `kb_get_document_type`         | Get a file's document type and proposed name and folder from saved entries, conventions and the complete listing.                                             | [document-type.schema.yaml](../contracts/extensions/mcp/v1/document-type.schema.yaml)                 |
| `kb_list_audiences`            | List the readers you can choose for a document type.                                                                                                          | [audiences.schema.yaml](../contracts/extensions/mcp/v1/audiences.schema.yaml)                         |
| `kb_list_convention_templates` | List bundled ACE, PARA and Johnny.Decimal definitions for notes, with folder purposes, naming suggestions and sources.                                        | [convention-templates.schema.yaml](../contracts/extensions/mcp/v1/convention-templates.schema.yaml)   |
| `kb_list_conventions`          | List naming and filing conventions that apply in a folder, with their source folders and parent marks.                                                        | [folder-conventions.schema.yaml](../contracts/extensions/mcp/v1/folder-conventions.schema.yaml)       |
| `kb_list_edits`                | List the edits recorded for `location`, oldest first, to check or undo an edit.                                                                               | [edits.schema.yaml](../contracts/extensions/mcp/v1/edits.schema.yaml)                                 |
| `kb_prepare_conventions`       | Prepare conventions text from supplied configuration and proposed changes.                                                                                    | [conventions-update.schema.yaml](../contracts/extensions/mcp/v1/conventions-update.schema.yaml)       |
| `kb_prepare_document_move`     | Prepare a document move from supplied text, a complete listing and permission.                                                                                | [document-move.schema.yaml](../contracts/extensions/mcp/v1/document-move.schema.yaml)                 |
| `kb_prepare_document_types`    | Prepare document-types text and filing assessments from supplied configuration, file changes and entries.                                                     | [document-types-update.schema.yaml](../contracts/extensions/mcp/v1/document-types-update.schema.yaml) |
| `kb_prepare_import`            | Prepare an import by splitting `text` into passages and listing questions for document types in the destination `folders`.                                    | [import.schema.yaml](../contracts/extensions/mcp/v1/import.schema.yaml)                               |
| `kb_record_edit`               | Record an edit right after you make it, so the person can check or undo the change.                                                                           | [edit.schema.yaml](../contracts/extensions/mcp/v1/edit.schema.yaml)                                   |
| `kbp_card`                     | Read the card for a document type before you draft or edit a document of that type.                                                                           | kbp's output, as is                                                                                   |
| `kbp_explore`                  | Write an offline HTML viewer for a universe spec under `explorer/` beside `log.jsonl`.                                                                        | kbp's output, as is                                                                                   |
| `kbp_inspect`                  | Get a universe spec and its type guidance as kbp's JSON model.                                                                                                | kbp's output, as is                                                                                   |
| `kbp_kinds`                    | List the document types of the universe specs that apply.                                                                                                     | kbp's output, as is                                                                                   |
| `kbp_mint`                     | Mint new `code` values of one `kind` for universe spec entries.                                                                                               | kbp's output, as is                                                                                   |
| `kbp_self_check`               | Validate kbp's bundled protocol definition with `kbp --self-check`.                                                                                           | kbp's output, as is                                                                                   |
| `kbp_validate`                 | Validate files in the nearest supplied `.knowledge-bus/` folder and parent files named in its `workspace.yaml`, using file text or digests from this session. | kbp's output, as is                                                                                   |
| `kbp_version`                  | Get the installed knowledge-bus release and protocol version from `kbp --version`.                                                                            | kbp's output, as is                                                                                   |

<!-- END AUTO-GENERATED tools -->

When kbp runs, the result contains one text block per non-empty stream, with stdout before stderr.
Each block identifies the stream in `_meta.stream`.
Tools with a `folders` argument can append a JSON text block with `_meta.stream` set to `knowledge-mcp`.
That block lists bundled or received universe specs and, after a successful `kbp_explore` call, the `explorer` folder.
The result contains the kbp exit code in `_meta.exit_code` and sets `isError` for a non-zero exit code.

Failures in `kb_*` tools and errors before kbp runs return a problem object in `structuredContent`.
[problem.schema.yaml](../contracts/extensions/mcp/v1/problem.schema.yaml) lists the problem types.

Each tool call adds a line to `log.jsonl` in the state folder. See [SECURITY.md](../SECURITY.md#trust-model).

## Arguments

<!-- BEGIN AUTO-GENERATED arguments -->

### `kb_get_document_type`

| Argument                | Type                                              | Required | Meaning                                                                                                                                                                                                                                                                                                             |
| ----------------------- | ------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `location`              | string                                            | yes      | A knowledge-base or document location as plain text. knowledge-mcp logs this text and never opens the location.                                                                                                                                                                                                     |
| `name`                  | string                                            | yes      |                                                                                                                                                                                                                                                                                                                     |
| `folders`               | list of string                                    | yes      | Folder names from the knowledge-base root down to the folder whose universe specs apply, such as `["docs", "rfcs"]`. Empty for the root folder.                                                                                                                                                                     |
| `knowledge_bus_folders` | list of [KnowledgeBusFolder](#knowledgebusfolder) | yes      | Every folder containing .knowledge-bus/, including peer folders. Include empty configuration folders. Classification uses the ancestors of the subject document; filing compares peers under the applicable universe specs.                                                                                         |
| `role`                  | string or null                                    | no       | The reader's role, such as maintainer. Prioritize document types by word overlap between this role and the reader role.                                                                                                                                                                                             |
| `record`                | string or null                                    | no       | The unedited text of `.knowledge-bus/plugins/knowledge-mcp/document-types.yaml` under the knowledge base root folder. When that file is missing, send the text of `.knowledge-bus/plugins/knowledge-mcp/record.yaml`, which knowledge-mcp 0.2.1 and earlier used. Send an empty string when both files are missing. |
| `record_digest`         | [Digest](#digest) or null                         | no       | Send the document-types digest from an earlier result in this session in place of `record` while the file remains unchanged.                                                                                                                                                                                        |
| `changes`               | list of [FileChange](#filechange) or null         | no       | Files changed since the document-types file was last saved. Send them with `record` or `record_digest`. knowledge-mcp applies the changes to the entries for this answer only.                                                                                                                                      |
| `listing`               | list of [ListedFile](#listedfile) or null         | no       |                                                                                                                                                                                                                                                                                                                     |
| `conventions`           | string or null                                    | no       | Current target conventions file text. Send empty text when the file is absent.                                                                                                                                                                                                                                      |
| `conventions_digest`    | string or null                                    | no       | Conventions digest received in this session. Reuse while the file remains unchanged.                                                                                                                                                                                                                                |
| `filing_values`         | list of [FilingValue](#filingvalue) or null       | no       |                                                                                                                                                                                                                                                                                                                     |
| `conventions_files`     | list of [ConventionFile](#conventionfile) or null | no       |                                                                                                                                                                                                                                                                                                                     |

### `kb_list_audiences`

| Argument                | Type                                              | Required | Meaning                                                                                                                                                                                                                                                                                                        |
| ----------------------- | ------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `location`              | string                                            | yes      | A knowledge-base or document location as plain text. knowledge-mcp logs this text and never opens the location.                                                                                                                                                                                                |
| `folders`               | list of string                                    | yes      | Folder names from the knowledge-base root down to the folder whose universe specs apply, such as `["docs", "rfcs"]`. Empty for the root folder.                                                                                                                                                                |
| `knowledge_bus_folders` | list of [KnowledgeBusFolder](#knowledgebusfolder) | yes      | One entry per folder that holds a `.knowledge-bus/` folder, from the root folder down to the target folder. Include `.knowledge-bus/` folders with no `*.kbp.yaml` file. If no entry has a `*.kbp.yaml` file or `workspace.yaml`, tools use the bundled universe specs. kbp_validate returns an error instead. |
| `document_type`         | string                                            | yes      | A document type id, such as `design-doc`.                                                                                                                                                                                                                                                                      |
| `universe_spec`         | string or null                                    | no       | Id of the universe spec to use when the document type appears in more than one universe spec that applies.                                                                                                                                                                                                     |

### `kb_list_convention_templates`

| Argument   | Type   | Required | Meaning                                                                                                         |
| ---------- | ------ | -------- | --------------------------------------------------------------------------------------------------------------- |
| `location` | string | yes      | A knowledge-base or document location as plain text. knowledge-mcp logs this text and never opens the location. |

### `kb_list_conventions`

| Argument                | Type                                              | Required | Meaning                                                                                                         |
| ----------------------- | ------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------- |
| `location`              | string                                            | yes      | A knowledge-base or document location as plain text. knowledge-mcp logs this text and never opens the location. |
| `folder`                | string                                            | yes      |                                                                                                                 |
| `knowledge_bus_folders` | list of [KnowledgeBusFolder](#knowledgebusfolder) | yes      |                                                                                                                 |
| `conventions_files`     | list of [ConventionFile](#conventionfile)         | yes      |                                                                                                                 |

### `kb_list_edits`

| Argument   | Type   | Required | Meaning                                                                                                         |
| ---------- | ------ | -------- | --------------------------------------------------------------------------------------------------------------- |
| `location` | string | yes      | A knowledge-base or document location as plain text. knowledge-mcp logs this text and never opens the location. |

### `kb_prepare_conventions`

| Argument                | Type                                                        | Required | Meaning                                                                                                         |
| ----------------------- | ----------------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------------- |
| `location`              | string                                                      | yes      | A knowledge-base or document location as plain text. knowledge-mcp logs this text and never opens the location. |
| `conventions`           | string or null                                              | no       | Current target conventions file text. Send empty text when the file is absent.                                  |
| `conventions_digest`    | string or null                                              | no       | Conventions digest received in this session. Reuse while the file remains unchanged.                            |
| `knowledge_bus_folders` | list of [KnowledgeBusFolder](#knowledgebusfolder)           | no       |                                                                                                                 |
| `changes`               | list of [Change](#change)                                   | no       |                                                                                                                 |
| `allowed_by`            | [AllowedBy](#allowedby) or null                             | no       |                                                                                                                 |
| `folder`                | string                                                      | no       |                                                                                                                 |
| `conventions_files`     | list of [ConventionFile](#conventionfile) or null           | no       |                                                                                                                 |
| `from_parent`           | list of [ConventionReference](#conventionreference) or null | no       |                                                                                                                 |

### `kb_prepare_document_move`

| Argument                | Type                                              | Required | Meaning                                                                                                                                                                                                                                                                                                             |
| ----------------------- | ------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `location`              | string                                            | yes      |                                                                                                                                                                                                                                                                                                                     |
| `old_path`              | [MovePath](#movepath)                             | yes      |                                                                                                                                                                                                                                                                                                                     |
| `path`                  | [MovePath](#movepath)                             | yes      |                                                                                                                                                                                                                                                                                                                     |
| `listing`               | list of [ListedFile](#listedfile)                 | yes      |                                                                                                                                                                                                                                                                                                                     |
| `documents`             | list of [MoveDocument](#movedocument)             | yes      |                                                                                                                                                                                                                                                                                                                     |
| `case_mode`             | `sensitive` or `insensitive`                      | yes      |                                                                                                                                                                                                                                                                                                                     |
| `allowed_by`            | [AllowedBy](#allowedby)                           | yes      |                                                                                                                                                                                                                                                                                                                     |
| `knowledge_bus_folders` | list of [KnowledgeBusFolder](#knowledgebusfolder) | yes      |                                                                                                                                                                                                                                                                                                                     |
| `record`                | string or null                                    | no       | The unedited text of `.knowledge-bus/plugins/knowledge-mcp/document-types.yaml` under the knowledge base root folder. When that file is missing, send the text of `.knowledge-bus/plugins/knowledge-mcp/record.yaml`, which knowledge-mcp 0.2.1 and earlier used. Send an empty string when both files are missing. |
| `record_digest`         | [Digest](#digest) or null                         | no       | Send the document-types digest from an earlier result in this session in place of `record` while the file remains unchanged.                                                                                                                                                                                        |
| `searched`              | boolean                                           | no       |                                                                                                                                                                                                                                                                                                                     |
| `search`                | list of string or null                            | no       |                                                                                                                                                                                                                                                                                                                     |
| `bindings`              | list of [LinkBinding](#linkbinding) or null       | no       |                                                                                                                                                                                                                                                                                                                     |

### `kb_prepare_document_types`

| Argument                | Type                                              | Required | Meaning                                                                                                                                                                                                                                                                                                             |
| ----------------------- | ------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `location`              | string                                            | yes      | The knowledge base root folder as plain text, such as a local path, a Drive folder link or a Notion page. knowledge-mcp logs this text and never opens the location.                                                                                                                                                |
| `record`                | string or null                                    | no       | The unedited text of `.knowledge-bus/plugins/knowledge-mcp/document-types.yaml` under the knowledge base root folder. When that file is missing, send the text of `.knowledge-bus/plugins/knowledge-mcp/record.yaml`, which knowledge-mcp 0.2.1 and earlier used. Send an empty string when both files are missing. |
| `record_digest`         | [Digest](#digest) or null                         | no       | Send the document-types digest from an earlier result in this session in place of `record` while the file remains unchanged.                                                                                                                                                                                        |
| `knowledge_bus_folders` | list of [KnowledgeBusFolder](#knowledgebusfolder) | no       | Every knowledge base folder that holds a `.knowledge-bus/` folder, even one with no `*.kbp.yaml` file. The bundled universe specs apply to a file when no `.knowledge-bus/` folder between the root and the file holds a `*.kbp.yaml` file or `workspace.yaml`.                                                     |
| `listing`               | list of [ListedFile](#listedfile) or null         | no       | Every file of the knowledge base outside `.knowledge-bus/` folders.                                                                                                                                                                                                                                                 |
| `changes`               | list of [FileChange](#filechange) or null         | no       | Files changed since the document-types file was last saved.                                                                                                                                                                                                                                                         |
| `entries`               | list of [EntryItem](#entryitem) or null           | no       | Send your document type choices and any document types or readers specified by the person.                                                                                                                                                                                                                          |
| `recheck`               | boolean or null                                   | no       | True to put every file with an entry back in `to_settle`, except files with a `set_by: person` entry.                                                                                                                                                                                                               |
| `allowed_by`            | [AllowedBy](#allowedby) or null                   | no       |                                                                                                                                                                                                                                                                                                                     |
| `conventions`           | string or null                                    | no       | Current target conventions file text. Send empty text when the file is absent.                                                                                                                                                                                                                                      |
| `conventions_digest`    | string or null                                    | no       | Conventions digest received in this session. Reuse while the file remains unchanged.                                                                                                                                                                                                                                |
| `filing_values`         | list of [FilingValue](#filingvalue) or null       | no       |                                                                                                                                                                                                                                                                                                                     |
| `conventions_files`     | list of [ConventionFile](#conventionfile) or null | no       |                                                                                                                                                                                                                                                                                                                     |

### `kb_prepare_import`

| Argument                | Type                                              | Required | Meaning                                                                                                                                                                                                                                                                                                        |
| ----------------------- | ------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `location`              | string                                            | yes      | The source document's location as plain text, such as a local path, a Drive link, a Notion page or `pasted in chat`. knowledge-mcp logs this text and never opens the location.                                                                                                                                |
| `text`                  | string                                            | yes      | The document's text, as read from its source or pasted by the person.                                                                                                                                                                                                                                          |
| `folders`               | list of string                                    | yes      | Folder names from the knowledge base root folder down to the destination folder. Empty for the root folder or when the person named no folder.                                                                                                                                                                 |
| `knowledge_bus_folders` | list of [KnowledgeBusFolder](#knowledgebusfolder) | yes      | One entry per folder that holds a `.knowledge-bus/` folder, from the root folder down to the target folder. Include `.knowledge-bus/` folders with no `*.kbp.yaml` file. If no entry has a `*.kbp.yaml` file or `workspace.yaml`, tools use the bundled universe specs. kbp_validate returns an error instead. |

### `kb_record_edit`

| Argument       | Type                    | Required | Meaning                                                                                                                           |
| -------------- | ----------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `location`     | string                  | yes      | A knowledge-base or document location as plain text. knowledge-mcp logs this text and never opens the location.                   |
| `allowed_by`   | [AllowedBy](#allowedby) | yes      |                                                                                                                                   |
| `before`       | string                  | yes      | The replaced text. Send an empty string for a new file.                                                                           |
| `after`        | string or null          | no       | The text that replaced `before`. Omit it only for a whole-file edit sent with `after_digest`.                                     |
| `after_digest` | string or null          | no       | The SHA-256 of `after` as UTF-8, written `sha256:` plus 64 lowercase hex digits. Replaces `after` only when `whole_file` is true. |
| `whole_file`   | boolean or null         | no       | True when `before` is the whole file.                                                                                             |

### `kbp_card`

| Argument                | Type                                              | Required | Meaning                                                                                                                                                                                                                                                                                                        |
| ----------------------- | ------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `location`              | string                                            | yes      | A knowledge-base or document location as plain text. knowledge-mcp logs this text and never opens the location.                                                                                                                                                                                                |
| `folders`               | list of string                                    | yes      | Folder names from the knowledge-base root down to the folder whose universe specs apply, such as `["docs", "rfcs"]`. Empty for the root folder.                                                                                                                                                                |
| `knowledge_bus_folders` | list of [KnowledgeBusFolder](#knowledgebusfolder) | yes      | One entry per folder that holds a `.knowledge-bus/` folder, from the root folder down to the target folder. Include `.knowledge-bus/` folders with no `*.kbp.yaml` file. If no entry has a `*.kbp.yaml` file or `workspace.yaml`, tools use the bundled universe specs. kbp_validate returns an error instead. |
| `kind`                  | string                                            | yes      | The document type id, such as `design-doc`.                                                                                                                                                                                                                                                                    |
| `universe`              | string or null                                    | no       | Id of the universe spec to use when several universe specs apply.                                                                                                                                                                                                                                              |

### `kbp_explore`

| Argument                | Type                                              | Required | Meaning                                                                                                                                                                                                                                                                                                        |
| ----------------------- | ------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `location`              | string                                            | yes      | A knowledge-base or document location as plain text. knowledge-mcp logs this text and never opens the location.                                                                                                                                                                                                |
| `folders`               | list of string                                    | yes      | Folder names from the knowledge-base root down to the folder whose universe specs apply, such as `["docs", "rfcs"]`. Empty for the root folder.                                                                                                                                                                |
| `knowledge_bus_folders` | list of [KnowledgeBusFolder](#knowledgebusfolder) | yes      | One entry per folder that holds a `.knowledge-bus/` folder, from the root folder down to the target folder. Include `.knowledge-bus/` folders with no `*.kbp.yaml` file. If no entry has a `*.kbp.yaml` file or `workspace.yaml`, tools use the bundled universe specs. kbp_validate returns an error instead. |
| `universe`              | string or null                                    | no       | Id of the universe spec to use when several universe specs apply.                                                                                                                                                                                                                                              |

### `kbp_inspect`

| Argument                | Type                                              | Required | Meaning                                                                                                                                                                                                                                                                                                        |
| ----------------------- | ------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `location`              | string                                            | yes      | A knowledge-base or document location as plain text. knowledge-mcp logs this text and never opens the location.                                                                                                                                                                                                |
| `folders`               | list of string                                    | yes      | Folder names from the knowledge-base root down to the folder whose universe specs apply, such as `["docs", "rfcs"]`. Empty for the root folder.                                                                                                                                                                |
| `knowledge_bus_folders` | list of [KnowledgeBusFolder](#knowledgebusfolder) | yes      | One entry per folder that holds a `.knowledge-bus/` folder, from the root folder down to the target folder. Include `.knowledge-bus/` folders with no `*.kbp.yaml` file. If no entry has a `*.kbp.yaml` file or `workspace.yaml`, tools use the bundled universe specs. kbp_validate returns an error instead. |
| `universe`              | string or null                                    | no       | Id of the universe spec to use when several universe specs apply.                                                                                                                                                                                                                                              |

### `kbp_kinds`

| Argument                | Type                                              | Required | Meaning                                                                                                                                                                                                                                                                                                        |
| ----------------------- | ------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `location`              | string                                            | yes      | A knowledge-base or document location as plain text. knowledge-mcp logs this text and never opens the location.                                                                                                                                                                                                |
| `folders`               | list of string                                    | yes      | Folder names from the knowledge-base root down to the folder whose universe specs apply, such as `["docs", "rfcs"]`. Empty for the root folder.                                                                                                                                                                |
| `knowledge_bus_folders` | list of [KnowledgeBusFolder](#knowledgebusfolder) | yes      | One entry per folder that holds a `.knowledge-bus/` folder, from the root folder down to the target folder. Include `.knowledge-bus/` folders with no `*.kbp.yaml` file. If no entry has a `*.kbp.yaml` file or `workspace.yaml`, tools use the bundled universe specs. kbp_validate returns an error instead. |
| `universe`              | string or null                                    | no       | Id of the universe spec to use when several universe specs apply.                                                                                                                                                                                                                                              |
| `format`                | `json` or `markdown` or null                      | no       | Defaults to `json`.                                                                                                                                                                                                                                                                                            |

### `kbp_mint`

| Argument                | Type                                              | Required | Meaning                                                                                                                                                                                                                                                                                                        |
| ----------------------- | ------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `location`              | string                                            | yes      | A knowledge-base or document location as plain text. knowledge-mcp logs this text and never opens the location.                                                                                                                                                                                                |
| `folders`               | list of string                                    | yes      | Folder names from the knowledge-base root down to the folder whose universe specs apply, such as `["docs", "rfcs"]`. Empty for the root folder.                                                                                                                                                                |
| `knowledge_bus_folders` | list of [KnowledgeBusFolder](#knowledgebusfolder) | yes      | One entry per folder that holds a `.knowledge-bus/` folder, from the root folder down to the target folder. Include `.knowledge-bus/` folders with no `*.kbp.yaml` file. If no entry has a `*.kbp.yaml` file or `workspace.yaml`, tools use the bundled universe specs. kbp_validate returns an error instead. |
| `kind`                  | `element`, `artifact`, `frame` or `factor`        | yes      |                                                                                                                                                                                                                                                                                                                |
| `count`                 | integer or null                                   | no       | Number of codes to mint, one by default.                                                                                                                                                                                                                                                                       |

### `kbp_self_check`

No arguments.

### `kbp_validate`

| Argument                | Type                                              | Required | Meaning                                                                                                                                                                                                                                                                                                        |
| ----------------------- | ------------------------------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `location`              | string                                            | yes      | A knowledge-base or document location as plain text. knowledge-mcp logs this text and never opens the location.                                                                                                                                                                                                |
| `folders`               | list of string                                    | yes      | Folder names from the knowledge-base root down to the folder whose universe specs apply, such as `["docs", "rfcs"]`. Empty for the root folder.                                                                                                                                                                |
| `knowledge_bus_folders` | list of [KnowledgeBusFolder](#knowledgebusfolder) | yes      | One entry per folder that holds a `.knowledge-bus/` folder, from the root folder down to the target folder. Include `.knowledge-bus/` folders with no `*.kbp.yaml` file. If no entry has a `*.kbp.yaml` file or `workspace.yaml`, tools use the bundled universe specs. kbp_validate returns an error instead. |

### `kbp_version`

No arguments.

<!-- END AUTO-GENERATED arguments -->

## Shapes

<!-- BEGIN AUTO-GENERATED shapes -->

### AllowedBy

| Field      | Type                                          | Required | Meaning                                                                                                                                                                                                |
| ---------- | --------------------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `basis`    | `request`, `instruction` or `accepted_change` | yes      | `request` means the person asked in this session. `instruction` means the person wrote an instruction for agents, such as in AGENTS.md. `accepted_change` means the person accepted a proposed change. |
| `text`     | string                                        | yes      | The request, instruction or accepted change, quoted.                                                                                                                                                   |
| `location` | string or null                                | no       | The file holding the instruction or the accepted change.                                                                                                                                               |

### Audience

| Field    | Type                     | Required | Meaning |
| -------- | ------------------------ | -------- | ------- |
| `value`  | string                   | yes      |         |
| `status` | `confirmed` or `guessed` | yes      |         |

### Change

Type: [UpsertConvention](#upsertconvention) or [RemoveConvention](#removeconvention).

### ConventionContent

| Field         | Type   | Required | Meaning |
| ------------- | ------ | -------- | ------- |
| `label`       | string | yes      |         |
| `instruction` | string | yes      |         |

### ConventionContentPart

| Field  | Type      | Required | Meaning |
| ------ | --------- | -------- | ------- |
| `part` | `content` | yes      |         |

### ConventionDatePart

| Field      | Type                              | Required | Meaning |
| ---------- | --------------------------------- | -------- | ------- |
| `part`     | `date`                            | yes      |         |
| `property` | string                            | yes      |         |
| `format`   | `YYYY-MM-DD`, `YYYY-MM` or `YYYY` | yes      |         |

### ConventionDocumentTypePart

| Field  | Type            | Required | Meaning |
| ------ | --------------- | -------- | ------- |
| `part` | `document_type` | yes      |         |

### ConventionFile

Type: [ConventionFile1](#conventionfile1) or [ConventionFile2](#conventionfile2).

### ConventionFile1

| Field    | Type                                    | Required | Meaning |
| -------- | --------------------------------------- | -------- | ------- |
| `folder` | [ConventionsFolder](#conventionsfolder) | yes      |         |
| `text`   | string                                  | yes      |         |
| `digest` | [Digest](#digest) or null               | no       |         |

### ConventionFile2

| Field    | Type                                    | Required | Meaning |
| -------- | --------------------------------------- | -------- | ------- |
| `folder` | [ConventionsFolder](#conventionsfolder) | yes      |         |
| `text`   | string or null                          | no       |         |
| `digest` | [Digest](#digest)                       | yes      |         |

### ConventionLiteralPart

| Field   | Type                                    | Required | Meaning |
| ------- | --------------------------------------- | -------- | ------- |
| `part`  | `literal`                               | yes      |         |
| `value` | [ConventionSegment](#conventionsegment) | yes      |         |

### ConventionName

| Field       | Type                            | Required | Meaning |
| ----------- | ------------------------------- | -------- | ------- |
| `separator` | ` `, `-` or `_`                 | yes      |         |
| `case`      | `as-written` or `lower` or null | no       |         |
| `parts`     | list of [Part](#part)           | yes      |         |

### ConventionPropertyPart

| Field      | Type       | Required | Meaning |
| ---------- | ---------- | -------- | ------- |
| `part`     | `property` | yes      |         |
| `property` | string     | yes      |         |

### ConventionReference

| Field           | Type   | Required | Meaning |
| --------------- | ------ | -------- | ------- |
| `universe_spec` | string | yes      |         |
| `document_type` | string | yes      |         |

### ConventionSegment

Type: string, pattern `^[^#|^:/\\\[\]\u0000-\u001f\u007f-\u009f]+$`.

### ConventionsFolder

Type: string, pattern `^(?:[^/\\\u0000]+(?:/[^/\\\u0000]+)*)?$`.

### Digest

Type: string, pattern `^sha256:[0-9a-f]{64}$`.

### EntryItem

| Field              | Type                          | Required | Meaning                                                                                                                                                               |
| ------------------ | ----------------------------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `path`             | string                        | yes      | Path from the knowledge-base root, folders joined by `/`, such as `docs/rfcs/0042-cache.md`.                                                                          |
| `set_by`           | [SetBy](#setby)               | yes      | `agent` when you chose the document type or reader. `person` when the person stated the document type or reader.                                                      |
| `universe_spec`    | string or null                | no       | Id of the universe spec that declares `document_type`.                                                                                                                |
| `document_type`    | string or null                | no       |                                                                                                                                                                       |
| `no_document_type` | boolean                       | no       |                                                                                                                                                                       |
| `audience`         | [Audience](#audience) or null | no       | The document's reader. `value` is one of the `choices` or the `actor` from `kb_list_audiences`. Set `status` to `confirmed` only after the person confirms the value. |

### FileChange

Type: [FileCreated](#filecreated) or [FileDeleted](#filedeleted) or [FileMoved](#filemoved) or [FileEdited](#fileedited).

### FileCreated

| Field         | Type                                | Required | Meaning |
| ------------- | ----------------------------------- | -------- | ------- |
| `change`      | `created`                           | yes      |         |
| `path`        | [Path](#path)                       | yes      |         |
| `fingerprint` | [Fingerprint](#fingerprint) or null | no       |         |

### FileDeleted

| Field    | Type          | Required | Meaning |
| -------- | ------------- | -------- | ------- |
| `change` | `deleted`     | yes      |         |
| `path`   | [Path](#path) | yes      |         |

### FileEdited

| Field         | Type                        | Required | Meaning |
| ------------- | --------------------------- | -------- | ------- |
| `change`      | `edited`                    | yes      |         |
| `path`        | [Path](#path)               | yes      |         |
| `fingerprint` | [Fingerprint](#fingerprint) | yes      |         |

### FileMoved

| Field         | Type                                | Required | Meaning                  |
| ------------- | ----------------------------------- | -------- | ------------------------ |
| `change`      | `moved`                             | yes      |                          |
| `path`        | [Path](#path)                       | yes      | The path after the move. |
| `old_path`    | [Path](#path)                       | yes      |                          |
| `fingerprint` | [Fingerprint](#fingerprint) or null | no       |                          |

### FilingValue

| Field           | Type           | Required | Meaning |
| --------------- | -------------- | -------- | ------- |
| `path`          | [Path](#path)  | yes      |         |
| `universe_spec` | string         | yes      |         |
| `document_type` | string         | yes      |         |
| `properties`    | object or null | no       |         |
| `content`       | string or null | no       |         |

### Fingerprint

Type: string.

### KnowledgeBusFolder

| Field            | Type                          | Required | Meaning                                                                             |
| ---------------- | ----------------------------- | -------- | ----------------------------------------------------------------------------------- |
| `folder`         | string                        | yes      | Path from the knowledge-base root, such as `team/notes`. Empty for the root folder. |
| `files`          | list of [SpecFile](#specfile) | no       | Every `*.kbp.yaml` file directly inside the `.knowledge-bus/` folder.               |
| `workspace_yaml` | string or null                | no       | The text of `.knowledge-bus/workspace.yaml`.                                        |

### LinkBinding

| Field         | Type                  | Required | Meaning |
| ------------- | --------------------- | -------- | ------- |
| `source_path` | [MovePath](#movepath) | yes      |         |
| `start`       | integer               | yes      |         |
| `end`         | integer               | yes      |         |
| `target_path` | [MovePath](#movepath) | yes      |         |

### ListedFile

| Field         | Type                                | Required | Meaning |
| ------------- | ----------------------------------- | -------- | ------- |
| `path`        | [Path](#path)                       | yes      |         |
| `fingerprint` | [Fingerprint](#fingerprint) or null | no       |         |

### MoveDocument

| Field  | Type                  | Required | Meaning |
| ------ | --------------------- | -------- | ------- |
| `path` | [MovePath](#movepath) | yes      |         |
| `text` | string                | yes      |         |

### MovePath

Type: string, pattern `^[^/\\\u0000]+(?:/[^/\\\u0000]+)*$`.

### Part

Type: [ConventionDocumentTypePart](#conventiondocumenttypepart) or [ConventionDatePart](#conventiondatepart) or [ConventionPropertyPart](#conventionpropertypart) or [ConventionContentPart](#conventioncontentpart) or [ConventionLiteralPart](#conventionliteralpart).

### Path

Type: string.

### RemoveConvention

| Field           | Type     | Required | Meaning |
| --------------- | -------- | -------- | ------- |
| `change`        | `remove` | yes      |         |
| `universe_spec` | string   | yes      |         |
| `document_type` | string   | yes      |         |

### SetBy

Type: `agent` or `person`.

### SpecFile

| Field     | Type           | Required | Meaning                                                                                                                                                                                          |
| --------- | -------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `name`    | string         | yes      | The file name, such as `universe.kbp.yaml`.                                                                                                                                                      |
| `id`      | string         | yes      | The `id` value in the file's `universe:` or `guidance:` block.                                                                                                                                   |
| `version` | string         | yes      | The `version` value in the file's `universe:` or `guidance:` block, as written.                                                                                                                  |
| `text`    | string or null | no       | The full file text. Send fresh text whenever the file changes. Reuse `digest` while the text stays unchanged. Leave it out when `id` and `version` match a bundled file, except in kbp_validate. |
| `digest`  | string or null | no       | The file's digest, as listed in `received` by an earlier tool result this session.                                                                                                               |

### UpsertConvention

| Field           | Type                                                             | Required | Meaning |
| --------------- | ---------------------------------------------------------------- | -------- | ------- |
| `change`        | `upsert`                                                         | yes      |         |
| `universe_spec` | string                                                           | yes      |         |
| `document_type` | string                                                           | yes      |         |
| `folder`        | list of [ConventionSegment](#conventionsegment) or [Part](#part) | yes      |         |
| `name`          | [ConventionName](#conventionname)                                | yes      |         |
| `content`       | [ConventionContent](#conventioncontent) or null                  | no       |         |
| `set_by`        | [SetBy](#setby)                                                  | yes      |         |

<!-- END AUTO-GENERATED shapes -->

## Terms

| Term          | Meaning                                                                                 |
| ------------- | --------------------------------------------------------------------------------------- |
| universe spec | A `*.kbp.yaml` file that declares document types and their questions                    |
| card          | A summary from `kbp_card` with sections, questions and conditions for one document type |
| kind          | In `kbp_card`, a document type id. In `kbp_mint`, the category of code to mint          |
| actor         | The role that uses a document type, such as maintainer                                  |
| element       | A question answered by a document section                                               |
| artifact      | A document type declared in a universe spec                                             |
| frame         | A setting used to order, select or require document types and sections                  |
| factor        | A question you can use to choose writing advice without changing document structure     |

## From the terminal

Run `kb type --help` for terminal usage.
