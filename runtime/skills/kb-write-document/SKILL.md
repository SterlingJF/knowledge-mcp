---
name: kb-write-document
description: Use before writing or editing a knowledge-base document, locally or through a connector.
---

# Write a Document

1. Read knowledge-base files with your own tools.
   Read `.knowledge-bus/plugins/knowledge-mcp/conventions.yaml` at the root. Use empty text when the file is absent.

2. **Get the document type.** Call `kb_get_document_type` with:
   - `location`: the file's path or URL, as text.
   - `name`: the filename, including its extension.
   - `folders`: the folder names on the path from the root folder to the file.
   - `knowledge_bus_folders`: every folder containing `.knowledge-bus/`, including folders holding peer documents. Set `folder` to its root-relative path. In `files`, list each `*.kbp.yaml` file directly inside the `.knowledge-bus/` directory by `name`. Include the `id` and `version` from the `universe:` or `guidance:` block. Include `text` when those values match no file bundled with knowledge-mcp. When `.knowledge-bus/workspace.yaml` exists, send its text as `workspace_yaml` on every call.
   - `role`: the reader's role, such as maintainer or product lead, when you can tell.
   - `listing`: every current document and attachment path relative to the root.
   - `record`: the current document-types file text. Follow `kb-track-document-types` for reading and migration.
   - `conventions`: the current root conventions text, or empty text when absent. Reuse `conventions_digest` only while the file remains unchanged.

   Send custom `*.kbp.yaml` text and the document-types file text once per session. On later calls, reuse the digest from `received` while the text is unchanged. Send a `*.kbp.yaml` digest as `digest` and the document-types digest as `record_digest`.

3. **Use the saved entry.** Read `recorded.entry` when the answer includes `recorded`. Use any saved `document_type`, `no_document_type` and `audience` values. Tell the person the entry comes from the document-types file.
4. **Choose a candidate.** Otherwise choose from `candidates`:
   - Compare each `actor` with the reader's role yourself, since `role_matches` compares words only.
   - When no candidate matched on the name, compare `every_document_type` with the file's outline and the conversation.
   - Ask the person to choose a document type only when several candidates remain.
   - When the reader's role is unclear, state your guess with "(guess)". Wait for the person to confirm the role before writing.
5. **Handle files without a document type.** If `no_document_type` is true or no document type describes the file, tell the person "no document type". Ask before writing. After approval, skip the card steps, write the document and follow the Edits section.
6. **Read naming values.** Read the convention for the chosen document type.
   Read each named property and any requested content value from the document.
   Send those values in `filing_values` with `path`, `universe_spec` and `document_type`, then repeat the lookup.
   Ask the person for unknown values. Never invent dates, properties or numbering.

7. **Review filing.** Show the assessment for the chosen document type and confirm the path before writing. Follow Names, folders and moves for an accepted move.
8. **Read the card.** Call `kbp_card` with `kind` set to the document type and the same `location` and `folders`, with ancestor `knowledge_bus_folders`. Set `universe` to the `universe_spec` of the chosen candidate or saved entry. Quote the card instead of restating its rules in your own words.
9. **Guess the conditions.** Read each condition after "Depends on:" on the card. State the expected value with "(guess)" and a reason. Keep the condition open until the person confirms or corrects the value. Write a conditional section only after the person confirms the values for that section. Show which sections depend on each open condition.
10. **Check whether a document is needed.** Read the card's "No document needed" line. Compare your guesses with any conditions. Treat "in every situation" as unconditional. If the line applies, say "no document needed (guess)" and name any assumed values. Ask whether to write the document anyway.
11. **Choose the reader.** Call `kb_list_audiences` with `document_type` and the same `location` and `folders`, with ancestor `knowledge_bus_folders`. Set `universe_spec` to the chosen universe spec id. When you can't tell the reader, ask the person and offer only the answer's `choices`. When `choices` is empty, write for the answer's `actor` and offer no choices of your own.
12. **Write.** Write the card's sections in order, follow the card's instructions, and use the confirmed values.

For card and reader calls, include only configuration folders from the root down to the subject folder.
Keep the complete peer-folder inventory for document-type lookup, tracking and move preparation.

## Conventions

1. Translate the requested folder and filename into structured parts.
   Show a rendered example and identify each value source.
   When converting a peer proposal, show any difference from the original proposal.
2. Get permission for each addition, replacement or removal.
   Call `kb_prepare_conventions` with `location` set to the root, current `conventions` text, proposed `changes` and `allowed_by`.
   Include current root definitions in `knowledge_bus_folders`, with custom universe spec text or an unchanged session digest.
3. Reread the file and compare its digest with `based_on` before writing.
   After a concurrent change, prepare again from fresh text and preserve unrelated conventions.
4. Save the returned `record` and record the edit through `kb_record_edit`.
   Keep an empty conventions file after removing the last convention.
   Existing files keep their names and folders until the person accepts a proposal.

## Names, folders and moves

Read `filing` for the chosen document type. Show the proposed name, folder and supporting files. When a convention applies, show the convention and its source file.
Mark a new folder explicitly.
Keep proposals for candidate types conditional until the person chooses a document type.
Keep writing at the existing path when the person declines a proposal.
A content edit authorizes a move only when the permission also covers the move.

1. Show the move, every referring document and the document-types update together.
   Get permission covering the complete operation: a request, an accepted proposal or a written instruction.
2. Call `kb_prepare_document_move` with `location`: the knowledge-base root, as text.
   Keep the same root across both move calls.
   Send the complete `listing`, the moved document in `documents`, and the current `record` or `record_digest`.
   Include `old_path`, accepted `path`, `case_mode`, peer and destination `knowledge_bus_folders`, and `allowed_by`.
3. When the answer returns `texts_needed`, search every Markdown file in the vault for every returned `search` string.
   Search encoded paths too; the returned percent marker includes files containing any URL escape.
   Use fixed strings and case-insensitive comparison, including Markdown files in hidden folders outside configuration and implementation directories.
   Read the full text of every matching file. Include the moved document even when the search finds no match.
   Call the tool again with those `documents`, `searched: true`, and `search` echoed exactly as returned.
   Repeat the search when the strings change. A search failure stops the move.
4. Resolve each blocking issue before applying writes. Establish ambiguous targets through Obsidian metadata or an independently verified vault resolver.
   Supply `bindings` with the source path, complete token range and target path. Offsets count Unicode code points.
   Case-dependent links and hand-written alias links also require established targets. Keep existing broken links unresolved.
5. Show any newly discovered referring documents and extend permission to cover those documents before applying writes.
6. Recheck the conventions digest before applying the proposal.
   After a changed convention, obtain a fresh proposal and renewed acceptance when the destination changes.
   Recheck the document-types and supplied document digests in `based_on`.
   Compare a fresh inventory with the supplied listing, including fingerprints.
   Reprepare from fresh inputs and repeat the search after any concurrent change. Keep unrelated changes from other sessions.
7. Create accepted missing folders with the move.
   Stage every replacement and retain every original, including the document-types text.
   Move the document without overwriting another file. Stage a case-only rename through a temporary path.
   Write every prepared document and the prepared document-types file as the same operation.
8. Verify every existing link target against the original target map, including outgoing links and links to other notes.
   Record each link text edit immediately through `kb_record_edit`, using the permission covering the operation.
   Report completion after verification.
9. After a write failure, restore originals when current digests still match the staged writes.
   Stop restoration when another session changed a file. Report each completed write, restored file and remaining conflict precisely.
   Several file writes provide no transaction across files.

## Edits

1. **Get permission.** Edit only with the person's permission. Otherwise, show the proposed text and ask for permission.
2. **Record each edit.** Immediately call `kb_record_edit` with `location`, `allowed_by`, `before` and `after`.
   Quote the person's words in `allowed_by.text` and select `allowed_by.basis`.
   For `instruction`, put the instruction file's path in `allowed_by.location`.
3. **Check or undo an edit.** Call `kb_list_edits` with `location`.
   Restore `before` only where the document still contains `after`.
   If the edit record omits `after`, restore the whole file from `before` only when the current file's digest equals `after_digest`.
4. **Update document types.** After creating, moving or deleting a file, follow `kb-track-document-types`.

During this work, commit nothing, push nothing, open no issue or pull request, and post no comment.
