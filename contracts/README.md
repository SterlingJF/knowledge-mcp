# contracts

## Folders

Put contracts for interfaces defined by other projects in `extensions/<target>/`.
Keep `document-types.schema.yaml` beside the tool result schemas so references between the schemas resolve.
Create `project/` for the first contract between modules in this repo.
Create `plugins/<name>/` for the first interface that knowledge-mcp defines for outside code.

## Layout

```text
contracts/
├── extensions/mcp/v1/               # Tool result, error and configuration schemas
│   ├── *.schema.yaml                # JSON Schemas and shared definitions
│   ├── tools.json                   # tools/list snapshot from the server
│   └── conformance/                 # Pass and fail samples per schema
└── package.json                     # Schema lint tool dependencies
```

## Naming

Name samples after `<name>.schema.yaml` in the same version folder.
Write fail samples by hand as `conformance/fail/<name>.<case>.yaml`.
`just generate_contract_snapshots` writes pass samples as `conformance/pass/<name>.<case>.yaml`.
`just check_contracts` fails when a pass sample fails its schema or a fail sample passes its schema.

## Schema Files

- Set `$schema` to JSON Schema 2020-12 and `$id` to the file name. Reference sibling schemas by file name, such as `problem.schema.yaml`.
- Give the root and each `$defs` entry a `title`, unique in the version folder. datamodel-codegen uses `title` to name generated classes.
- Use draft-07 keywords plus `$defs` for compatibility with the TypeScript MCP SDK client. The client validates each `outputSchema` with draft-07 Ajv. Avoid `unevaluatedProperties`, `dependentRequired`, `prefixItems` and `$dynamicRef`. Draft-07 Ajv ignores those keywords.
- Include `object` in `type` for each subschema with `required` or `properties`. List each `required` name under `properties` in the same subschema.

## Commands

| Command                | Purpose                                                                                                      |
| ---------------------- | ------------------------------------------------------------------------------------------------------------ |
| `just check_contracts` | Lint schemas and `tools.json`, validate samples, check that `runtime/knowledge_mcp/schemas_auto/` is current |

## Versions

Each successful `kb_*` result has a `schema` field with a schema ID, such as `knowledge-mcp/document-type/1`.
The document-types file has `schema: knowledge-mcp/document-types/1`.
The template catalog uses `knowledge-mcp/convention-templates/1`.
The folder, name and content definitions come from `conventions.schema.yaml`.
Templates describe proposals; saved conventions contain accepted patterns without a template dependency.
The root conventions file has `schema: knowledge-mcp/conventions/1`.
Filing assessments add convention sources and missing values while retaining their `/1` schema IDs.
Raise the schema version when the stored file changes, or when an answer field is removed or renamed, changes meaning or becomes narrower.
A new answer field keeps the version. The server publishes output schemas in `tools/list` and validates its structured answers against them.

`kb_*` tool errors include an RFC 9457 `type` field with a problem type URI.
Give a problem type a new URI when its meaning changes.

Contract tests live in `runtime/tests/test_contract_snapshots.py` and `runtime/tests/test_contract_end_to_end.py`.

## Team conventions

`folder-conventions.schema.yaml` describes `kb_list_conventions` answers. Supply a `conventions_files` entry for each relevant `.knowledge-bus/` folder. Use empty text to mark an absent file; an existing empty file is invalid. After sending full text, reuse the returned digest only while the file remains unchanged.

A team's conventions file establishes a boundary: parent conventions apply only when explicitly selected from declarations in the nearest parent file. Selected conventions still file relative to their declaring folder. Answers identify each convention's source folder and file, digest, accepted pattern and whether it comes from a parent. Use that evidence to explain proposals and check for changed configuration before applying them.

The answer lists inactive declarations when a document type is unavailable or its universe spec definition differs. Resolve those issues before preparing moves. The older `conventions` and `conventions_digest` arguments describe root configuration; send either those arguments or explicit `conventions_files`, never both.

## Preparing moves together

`kb_prepare_document_moves` resolves links against the original inventory and prepares all destinations together. Search every Markdown document for the returned search strings, supply matching documents in full, and echo the strings exactly with search confirmation. Without permission, the answer previews affected documents. With `allowed_by` and no blocking issues, it returns replacement text and a prepared document-types file. Non-ready answers contain empty writes and a null record.

The agent must recheck the inventory, configuration and document digests before applying changes. It applies the moves and link repairs, verifies targets and records each final write. The [writing skill](../runtime/skills/kb-write-document/SKILL.md#many-files-at-once) defines application, recovery and undo requirements.

Edit answers use `knowledge-mcp/edit/2` and `knowledge-mcp/edits/2`; their schema files remain in the `v1` contract directory. Optional operation metadata groups whole-file edits for whole-list undo, which requires complete records and matching current file digests. Listing still reads ungrouped entries and converts legacy permission fields. Document-types and conventions stored formats remain at `/1`.
