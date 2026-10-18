# contracts

## Folders

Put contracts for interfaces defined by other projects in `extensions/<target>/`.
Keep `document-types.schema.yaml` beside the tool result schemas so references between the schemas resolve.
Create `project/` for the first contract between modules in this repo.
Create `plugins/<name>/` for the first interface that knowledge-mcp defines for outside code.

## Layout

```text
contracts/
├── extensions/mcp/v1/               # Tool result, error and document-types schemas
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
Raise the schema version for a breaking change:

- a field removed or renamed;
- a narrower type or value list;
- a new required field;
- a field whose meaning changes.

Raise the schema version before emitting a new field that older schemas reject.

`kb_*` tool errors include an RFC 9457 `type` field with a problem type URI.
Give a problem type a new URI when its meaning changes.

## Related Locations

| Item           | Location                                                                                |
| -------------- | --------------------------------------------------------------------------------------- |
| Contract tests | `runtime/tests/test_contract_snapshots.py`, `runtime/tests/test_contract_end_to_end.py` |
