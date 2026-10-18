---
name: kb-write-document
description: Use before writing or editing a knowledge-base document, locally or through a connector.
---

# Write a Document

1. Read knowledge-base files with your own tools.

2. **Get the document type.** Call `kb_get_document_type` with:
   - `location`: the file's path or URL, as text.
   - `folders`: the folder names on the path from the root folder to the file.
   - `knowledge_bus_folders`: each folder on that path containing `.knowledge-bus/`. Set `folder` to its root-relative path. In `files`, list each `*.kbp.yaml` file directly inside the `.knowledge-bus/` directory by `name`. Include the `id` and `version` from the `universe:` or `guidance:` block. Include `text` when those values match no file bundled with knowledge-mcp. When `.knowledge-bus/workspace.yaml` exists, send its text as `workspace_yaml` on every call.
   - `role`: the reader's role, such as maintainer or product lead, when you can tell.
   - `record`: the current document-types file text. Follow `kb-track-document-types` for reading and migration.

   Send custom `*.kbp.yaml` text and the document-types file text once per session. On later calls, reuse the digest from `received` while the text is unchanged. Send a `*.kbp.yaml` digest as `digest` and the document-types digest as `record_digest`.

3. **Use the saved entry.** Read `recorded.entry` when the answer includes `recorded`. Use any saved `document_type`, `no_document_type` and `audience` values. Tell the person the entry comes from the document-types file.
4. **Choose a candidate.** Otherwise choose from `candidates`:
   - Compare each `actor` with the reader's role yourself, since `role_matches` compares words only.
   - When no candidate matched on the name, compare `every_document_type` with the file's outline and the conversation.
   - Ask the person to choose a document type only when several candidates remain.
   - When the reader's role is unclear, state your guess with "(guess)". Wait for the person to confirm the role before writing.
5. **Handle files without a document type.** If `no_document_type` is true or no document type describes the file, tell the person "no document type". Ask before writing. After approval, skip the card steps, write the document and follow the Edits section.
6. **Read the card.** Call `kbp_card` with `kind` set to the document type and the same `location`, `folders` and `knowledge_bus_folders`. Set `universe` to the `universe_spec` of the chosen candidate or saved entry. Quote the card instead of restating its rules in your own words.
7. **Guess the conditions.** Read each condition after "Depends on:" on the card. State the expected value with "(guess)" and a reason. Keep the condition open until the person confirms or corrects the value. Write a conditional section only after the person confirms the values for that section. Show which sections depend on each open condition.
8. **Check whether a document is needed.** Read the card's "No document needed" line. Compare your guesses with any conditions. Treat "in every situation" as unconditional. If the line applies, say "no document needed (guess)" and name any assumed values. Ask whether to write the document anyway.
9. **Choose the reader.** Call `kb_list_audiences` with `document_type` and the same `location`, `folders` and `knowledge_bus_folders`. Set `universe_spec` to the chosen universe spec id. When you can't tell the reader, ask the person and offer only the answer's `choices`. When `choices` is empty, write for the answer's `actor` and offer no choices of your own.
10. **Write.** Write the card's sections in order, follow the card's instructions, and use the confirmed values.

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
