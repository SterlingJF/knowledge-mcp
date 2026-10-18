---
name: kb-track-document-types
description: Use at session start and after creating, moving or deleting a knowledge-base file.
---

# Track Document Types

1. **Read the document-types file.** Read `.knowledge-bus/plugins/knowledge-mcp/document-types.yaml` at the root folder with your own tools.
   If missing, read `.knowledge-bus/plugins/knowledge-mcp/record.yaml` for migration.
   Use an empty string when both files are missing.
   Read conventions along every affected ancestor path at session start.
   Send `conventions_files` as `kb-write-document` describes, including explicit absence markers.
   Reuse each file digest while its text remains unchanged.
2. **Compare the complete inventory.** Enumerate the whole root with your own tools, including nested knowledge-base folders and relevant attachments.
   Stop after an incomplete listing or enumeration failure. Send a listing only after enumeration succeeds.
   Call `kb_prepare_document_types` with:
   - `location`: the root folder, as text.
   - `record`: the text read in the previous step.
   - `listing`: every file outside `.knowledge-bus/`, with root-relative `path` values. Add a `fingerprint` when cheap to compute.
   - `knowledge_bus_folders`: every folder containing `.knowledge-bus/`, sent as `kb-write-document` describes.

   Retain the initial `listing_changes` through classification and naming-value calls until the prepared record is saved.
   Follow-up answers can omit `listing_changes`; keep the initial events for the session-start report.
   Use `listing_changes` for observed events and `changed` for prepared entry changes.

   **Prepare the session-start review.** Follow Choose document types below for arrivals and unresolved move destinations.
   Read file content when the name and folder leave the document type unclear.
   Follow `kb-write-document` to collect recorded naming values; keep missing titles, dates and numbers as questions.
   Join each assessment by current path, universe spec and document type after choosing the type.
   Keep candidate proposals conditional; several candidates give no single proposal.
   Assess every typed arrival and external move, using conventions in effect at the current path and their provenance.
   Without a convention, use peers within the applicable universe specs.
   Explain `already_matches`, missing peers, incomplete evidence, occupied destinations and destination type conflicts.
   List `values_needed` beside the affected file and ask for the missing values.
   Preserve the original entry when an external move reaches a folder without the saved document type.
   Resolve that conflict before preparing another move.
   Combine saved `no_document_type` entries with the current listing and `to_settle` to list files that still need a document type.
   Keep explicit no-document-type entries until the person requests another classification; avoid repeated classification questions.
   Deduplicate unresolved files by current path and include their event labels.

   **Show the session-start review.** Say: “Compared the current listing with the document-types file.”
   An empty record establishes no arrival dates; describe the inventory as new to the record.
   Claim “since the last session” only when the saved record establishes that baseline.
   Give complete counts for new, moved, deleted and fingerprint-update events before showing files.
   Order groups as new files, moved files, deleted files, fingerprint updates and unresolved files.
   Sort each group by current root-relative path in Unicode code-point order; sort deletions by the former path.
   Preview at most 50 distinct files across all groups, counting each unresolved file once.
   State the number shown, the total and the number omitted, even when no file is omitted.
   Keep the complete listing, event arrays and assessments; the cap limits the conversational preview alone.
   Summarize fingerprint-only updates as counts unless the person asks for details.
   A first fingerprint establishes a baseline; claim changed content only when earlier fingerprints establish a difference.
   Retain classifications after content changes and review filing on request.
   Show old paths, retained classifications and assessments beside moved files.
   Report discovered link problems after external moves; claim link repairs only after verifying the repairs.
   Describe basename fallback pairs as observed moves without claiming verified content identity.
   Leave ambiguous move pairs as arrivals and deletions, and give deleted files no filing proposal.
   Describe unsaved entry changes as prepared changes.
   Obtain classification-save permission separately from move permission.
   Route one accepted proposal through `kb_prepare_document_move` and several through `kb_prepare_document_moves`.
   Before acceptance, show the complete selected move list, every affected document and every new folder, including rows omitted from the preview.
   Follow the existing search, digest, application, recovery and edit-recording sequence in `kb-write-document`.
   Report completed moves and verified repairs after application.

3. **Update after each file change.** Keep the complete listing current after creates, moves, renames, edits and deletions. After each change, call `kb_prepare_document_types` with the same `location` and `knowledge_bus_folders`. Include `changes` and the current `record` or `record_digest`.
   After saving `record`, send the returned `digest` as `record_digest` instead of `record` on the next call.
   Follow any `note` in `changed`.
4. **Review names and folders.** Resolve conventions separately for each document.
   Keep peer evidence within the applicable universe specs. Report broken parent selections before proposing moves.
   Show missing naming values beside each affected typed file.
   Follow `kb-write-document` to collect values for a file under review. Show `filing` proposals beside typed files. Keep proposals conditional while choosing a document type.
   Prepare accepted moves through the Names, folders and moves sequence in `kb-write-document` before changing files.
   Save the prepared document-types text with the move and link repairs. Valid moves retain every classification field.
   Resolve destination type conflicts explicitly, preserving the original entry while choosing another folder or changing universe specs separately.

5. **Choose document types.** For each file in `to_settle`, follow `kb-write-document` to choose from `candidates`, as for `kb_get_document_type`.
   If no candidate matches the file name, use `every_document_type` from the `scopes` item at the file's `scope` index.
   Send each choice in `entries` with `path`, `universe_spec` and `document_type`. Set `set_by` to `agent`.
   For an untyped file, set `no_document_type` to true instead of sending `universe_spec` and `document_type`.
   Put the reader in `audience.value` when known.
   Set `audience.status` to `confirmed` after the person confirms the reader, and to `guessed` otherwise.
6. **Record corrections.** When the person names another document type, no document type, or another reader, send the corrected entry with `set_by` set to `person`.
   Send `allowed_by` with `basis` set to `request` and the person's words in `text`.
7. **Get permission to save.** Save only with the person's permission.
   Send permission to `kb_prepare_document_types` as `allowed_by`, following the Edits section of `kb-write-document`.
   Without permission, show the proposed entry changes and ask for permission to save.
8. **Save the returned text.** If `record` is null, skip the save. Otherwise, repeat the file-reading step to get the current text before saving.
   - If the digest of the current text equals `based_on`, save `record` immediately. Create missing folders with your own tools.
   - If the text changed, call `kb_prepare_document_types` with the new text, the same `changes`, `entries` and `allowed_by`, and no `listing`.
     If the first call sent `listing`, add the first returned `listing_changes` to `changes`.

   For migration, save the converted `record` as `document-types.yaml`.
   Delete `record.yaml` only with the person's permission.

9. **Recheck on request.** When the person requests a recheck, set `recheck` to true. The tool preserves entries with `set_by: person`.
   Choose a document type for each file in `to_settle`.
   After an accepted convention change, refresh filing assessments on request.
   Keep existing document paths until a proposal is accepted.
   Keep convention changes separate from classification changes and document moves.
10. **Keep entries in the document-types file.** Change entries through `kb_prepare_document_types` or the prepared document-types text from `kb_prepare_document_move` or `kb_prepare_document_moves`.
    Keep document text out of the document-types file.

For requested starter conventions, follow Templates in `kb-write-document`.
At session start, read saved conventions without reapplying templates or replacing accepted patterns.
Keep classification permission, configuration permission and move permission separate.

For many proposals, request a folder review through `filing_review` with a complete listing.
Follow Many files at once in `kb-write-document` for changes, drops, acceptance and application.
Keep unresolved classifications and missing naming values visible.
Save the complete prepared document-types update with the accepted moves.
Avoid intermediate tracking updates while files occupy temporary paths.
Refresh the inventory after completion without replaying moves already represented by the prepared record.
