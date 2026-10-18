---
name: kb-track-document-types
description: Use at session start and after creating, moving or deleting a knowledge-base file.
---

# Track Document Types

1. **Read the document-types file.** Read `.knowledge-bus/plugins/knowledge-mcp/document-types.yaml` at the root folder with your own tools.
   If missing, read `.knowledge-bus/plugins/knowledge-mcp/record.yaml` for migration.
   Use an empty string when both files are missing.
2. **Start the session.** Call `kb_prepare_document_types` with:
   - `location`: the root folder, as text.
   - `record`: the text read in the previous step.
   - `listing`: every file outside `.knowledge-bus/`, with root-relative `path` values. Add a `fingerprint` when cheap to compute.
   - `knowledge_bus_folders`: every folder containing `.knowledge-bus/`, sent as `kb-write-document` describes.

   Keep `listing_changes` until you save the returned `record`.

3. **Update after each file change.** After creating, moving or deleting a file, call `kb_prepare_document_types` with the same `location` and `knowledge_bus_folders`. Include `changes` and the current `record` or `record_digest`.
   After saving `record`, send the returned `digest` as `record_digest` instead of `record` on the next call.
   Follow any `note` in `changed`.
4. **Choose document types.** For each file in `to_settle`, follow `kb-write-document` to choose from `candidates`, as for `kb_get_document_type`.
   If no candidate matches the file name, use `every_document_type` from the `scopes` item at the file's `scope` index.
   Send each choice in `entries` with `path`, `universe_spec` and `document_type`. Set `set_by` to `agent`.
   For an untyped file, set `no_document_type` to true instead of sending `universe_spec` and `document_type`.
   Put the reader in `audience.value` when known.
   Set `audience.status` to `confirmed` after the person confirms the reader, and to `guessed` otherwise.
5. **Record corrections.** When the person names another document type, no document type, or another reader, send the corrected entry with `set_by` set to `person`.
   Send `allowed_by` with `basis` set to `request` and the person's words in `text`.
6. **Get permission to save.** Save only with the person's permission.
   Send permission to `kb_prepare_document_types` as `allowed_by`, following the Edits section of `kb-write-document`.
   Without permission, show the proposed entry changes and ask for permission to save.
7. **Save the returned text.** If `record` is null, skip the save. Otherwise, repeat the file-reading step to get the current text before saving.
   - If the digest of the current text equals `based_on`, save `record` immediately. Create missing folders with your own tools.
   - If the text changed, call `kb_prepare_document_types` with the new text, the same `changes`, `entries` and `allowed_by`, and no `listing`.
     If the first call sent `listing`, add the first returned `listing_changes` to `changes`.

   For migration, save the converted `record` as `document-types.yaml`.
   Delete `record.yaml` only with the person's permission.

8. **Recheck on request.** When the person requests a recheck, set `recheck` to true. The tool preserves entries with `set_by: person`.
   Choose a document type for each file in `to_settle`.
9. **Keep entries in the document-types file.** Change entries only through `kb_prepare_document_types`.
   Keep document text out of the document-types file.
