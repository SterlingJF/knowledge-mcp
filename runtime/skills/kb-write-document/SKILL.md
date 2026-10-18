---
name: kb-write-document
description: Use before writing or editing a knowledge-base document, locally or through a connector.
---

# Write a Document

1. Read knowledge-base files with your own tools.
   Establish the root and the requested folder. Discover `.knowledge-bus/` folders along every relevant ancestor path.
   Read `.knowledge-bus/plugins/knowledge-mcp/conventions.yaml` under each supplied configuration folder.
   Record explicit absence for missing files. An existing empty file is invalid.

2. **Get the document type.** Call `kb_get_document_type` with:
   - `location`: the file's path or URL, as text.
   - `name`: the filename, including its extension.
   - `folders`: the folder names on the path from the root folder to the file.
   - `knowledge_bus_folders`: every folder containing `.knowledge-bus/`, including folders holding peer documents. Set `folder` to its root-relative path. In `files`, list each `*.kbp.yaml` file directly inside the `.knowledge-bus/` directory by `name`. Include the `id` and `version` from the `universe:` or `guidance:` block. Send complete local `*.kbp.yaml` text on first use, including files with bundled ids and versions. When `.knowledge-bus/workspace.yaml` exists, send its text as `workspace_yaml` on every call.
   - `role`: the reader's role, such as maintainer or product lead, when you can tell.
   - `listing`: every current document and attachment path relative to the root.
   - `record`: the current document-types file text. Follow `kb-track-document-types` for reading and migration.
   - `conventions_files`: each relevant configuration folder and its complete conventions `text`; send empty text for an absent file.
     Use `folder: ""` for the root. Reuse `digest` from `received` while the file remains unchanged.

   Send the document-types file text once per session. On later calls, reuse the digest from `received` while the text is unchanged. Send a `*.kbp.yaml` digest as `digest` and the document-types digest as `record_digest`.

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

## Folder conventions

Call `kb_list_conventions` when the person asks which conventions apply in a folder.
Send the root, requested `folder`, current `knowledge_bus_folders` and explicit `conventions_files`.
Show each convention, its declaring folder, parent mark and inactive reason.
Resolve broken parent selections before proposing moves.
A selected convention keeps its declaring folder as the filing base.
For example, a company convention using `Contracts` still files under the company folder when Finance selects the convention.
Save a reviewed local convention to file under `Finance/Contracts`.

## Templates

1. Read conventions and current universe specs for the selected folder.
   List every document type through `kbp_kinds`.
   Identify note document types and explicitly list excluded codebase records.
   Keep universe spec changes with the knowledge-bus skills.
2. Call `kb_list_convention_templates` for the bundled definitions and sources.
   Ask which pattern to use when the person has not chosen a pattern.
   Map every note document type by its declared purpose and relevant note content.
   Read `kbp_card` when a purpose remains unclear. Filename keywords alone cannot decide the assignment.
   Keep unfamiliar types and unresolved mappings visible with a specific question.
3. Start ACE with Atlas, Calendar and Efforts.
   Credit ACE for folder purposes, and knowledge-mcp for title and meeting-note naming suggestions.
   Daily notes use a recorded date alone; other Calendar notes use a recorded date and title.
   Replace the suggested `date` property with the actual recorded property before acceptance.
   Never derive dates from the current date or filesystem timestamps.
4. For customized ACE, preserve the person's actual folder names and confirm each assignment.
   Ask for the actual daily-note and meeting-note folders rather than inventing a Calendar equivalent.
   Never infer authorship from folder spelling.
   For a document type spanning several folders, recommend a single chosen folder.
   Offer a dynamic folder from a named recorded property when the notes already distinguish the folders.
   Discuss distinct document types through the knowledge-bus skills separately.
5. For PARA, propose Projects, Areas, Resources and Archives by purpose.
   Credit knowledge-mcp for title naming and suggested property names.
   Add project, area or topic subfolders from recorded properties after review.
   Preserve accepted numbered prefixes. Review active and archived placement explicitly.
6. For Johnny.Decimal, ask for existing or person-supplied area, category and ID folders and unknown numbers.
   Check that the category number belongs within the area range and the ID begins with the category number.
   Request correction or clarification for invalid or unusual relationships before saving a Johnny.Decimal proposal.
   Preserve supplied numbers, titles and prefixes. Put notes directly inside the accepted ID folder.
   Use the recorded date and title; include a recorded filename ID only after explicit acceptance.
   Never allocate numbers, generate a JDex or invent an ID folder.
7. Show a proposal or a blocking question for every note document type.
   Include the existing convention, proposed folder, naming parts, property and content sources, and a rendered example.
   Construct `knowledge-mcp/conventions/1` text in memory and call `kb_get_document_type` with supplied naming values for previews.
   Mark new folders from the inventory and check existing empty folders with your own tools.
   Proposed note folders wait for accepted moves.
8. Collect an accept, change or drop answer for each proposal.
   Preserve existing conventions when proposals are dropped. Explain replacements before requesting acceptance.
   Keep unresolved proposals pending or explicitly dropped.
   Resolve two proposals for the same universe spec and document type through a choice or a reviewed combined pattern.
   Combine accepted patterns from different templates in the same conventions file.
   Use `set_by: agent` for template suggestions and `set_by: person` for conventions the person states.
   Keep attribution separate from permission.
9. Save accepted changes through Conventions below, with complete definitions for the selected folder.
   Skip the configuration write when every proposal is dropped.
   Saving conventions leaves note paths, note bytes and classifications unchanged.
   Apply each accepted move through Names, folders and moves, including both preparation calls and every link repair.

## Conventions

1. Translate the requested folder and filename into structured parts.
   Show a rendered example and identify each value source.
   When converting a peer proposal, show any difference from the original proposal.
2. Get permission for each addition, replacement or removal.
   Call `kb_prepare_conventions` with `location` set to the root, current `conventions` text, proposed `changes` and `allowed_by`.
   Set `folder` to the selected folder and supply ancestor `conventions_files`, excluding the target file.
   Include current applicable definitions in `knowledge_bus_folders`, with complete local universe spec text or an unchanged session digest.
   Send `from_parent` to replace the complete parent selection; omission preserves the current selection.
   Preview every resulting convention before creating a team boundary or changing parent selections.
   Keep template proposals local to the selected folder. Choose parent selections explicitly.
3. Reread target text, parent conventions and universe spec configuration before writing.
   Compare the target digest with `based_on`.
   After a concurrent change, prepare again from fresh text and preserve unrelated conventions.
4. Save the returned `record` and record the edit through `kb_record_edit`.
   Keep valid conventions YAML with `conventions: []` after removing the last local convention.
   Preserve accepted `from_parent` selections and the saved boundary.
   Reread saved text and repeat preparation after saving.
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
   Recheck target conventions, parent conventions and applicable universe spec configuration.
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

## Many files at once

1. Request `kb_prepare_document_types` with `filing_review.folder` and a complete vault listing.
   Review direct children by default; set `recursive: true` when the person includes subfolders.
   Resolve document types and read naming values from the original documents.
   Keep unknown types and missing values visible with specific questions.
2. Show the complete proposal list in original-path order, with convention sources or peer evidence and new folders.
   Identify rows by original path. Retain each original reason when the person chooses a different destination.
   Record the person's choice separately; changing a destination changes no saved convention.
   Recompute the complete remaining list after every change or drop.
   An occupied name becomes available only when another accepted row vacates the name.
   Keep blocked rows visible until the person explicitly drops or corrects each blocked row.
   Skip all writes when every row is dropped.
3. Prepare the complete list through `kb_prepare_document_moves`, with every moved document and current configuration.
   Never prepare an accepted list by looping over `kb_prepare_document_move`.
   Search every Markdown document using the exact returned strings, including files outside the reviewed folder.
   Follow the fixed-string, case-insensitive search and binding rules in Names, folders and moves.
   Include full matching text and every moved document; echo `search` exactly with `searched: true`.
   A failed search stops preparation. Changed inputs require a fresh search.
4. Show the final moves, required folders, affected documents, link repairs and document-types update before acceptance.
   Obtain permission for the exact complete list and repeat preparation with `allowed_by`.
   A changed destination or newly affected document requires a revised preview and renewed acceptance.
   Reuse permission when fresh preparation has identical approved effects.
   Explain row or byte limits before acceptance and ask for a smaller explicit review.
   Never divide an accepted list into independently prepared groups.
5. Recheck the listing, document digests, document-types digest, naming values and configuration digests.
   Reprepare after changed inputs. Retain original paths and bytes, replacement bytes and write progress.
   Allocate an unused staging directory outside link discovery and verify every temporary name is unused.
   Stage all moving originals without overwriting files, including swaps, cycles and case-only renames.
   Confirm final destinations are vacant, then install moving documents and stationary referring replacements.
   Save the prepared document-types file last. Create only accepted missing folders.
6. Record each final write immediately through `kb_record_edit`, including unchanged-text renames and the document-types file.
   Use the root as `location`, `whole_file: true`, original `before` and final `after` or `after_digest`.
   Supply `operation` with an opaque `id`, original `old_path`, final `path`, and positive `index` and `count`.
   Give all records the same operation id and total count; assign each index once.
   Stationary referring documents use equal original and final paths.
7. Verify final paths, bytes, classifications, every original link target and every required edit record.
   Remove staging material after successful verification. Several writes provide no transaction across files.
   After failure, stop forward writes and restore only files whose current path and bytes match the operation's output.
   Stage installed destinations before restoring originals, so swap recovery preserves both notes.
   Preserve concurrent changes. Restore referring documents and configuration from retained originals when digest guards pass.
   Remove new folders only when empty and created by this operation.
   Retain recovery material until restoration finishes.
   Report completed writes, restored files, temporary files, conflicting files and missing edit records.
   After a failed recording call, list the operation records before retrying.
   Reuse an existing matching operation index and record only missing indices.
   Retry recording from retained text without repeating filesystem writes. Claim completion after recording succeeds.
8. For whole-list undo, retrieve grouped records through `kb_list_edits(location=root)`.
   Verify the complete count, unique indices, final paths and after digests, including the document-types file.
   Block automatic undo and list conflicts after later changes or an incomplete group.
   Present the complete inverse list and restoration effects, then obtain permission.
   Prepare inverse moves together through `kb_prepare_document_moves`.
   Restore recorded original text through the same staging and digest guards.
   Restore document-types text only while its recorded after digest matches current text.
   Verify restored targets and record the undo edits.
