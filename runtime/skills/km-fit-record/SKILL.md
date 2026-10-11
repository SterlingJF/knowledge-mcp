---
name: km-fit-record
description: Keep a knowledge base's fit record as files are created, moved and deleted, so every session and chat knows each file's universe spec and document type at once. Saves only on the person's request or under a standing line the person wrote, names that line, and keeps the person's corrections.
---

# Keep the Fit Record

**Purpose: when the person works on any file, in any session or chat, its document type is already known, so the help is instant and the same everywhere.**

The fit record is `record.yaml` in `.knowledge-bus/plugins/knowledge-mcp/`, knowledge-mcp's own plugin folder, at the knowledge base's top folder. Create the folders when missing. `kbp` reads only the files directly inside `.knowledge-bus/`, so the record changes no universe spec in scope. Each entry names a file's universe spec and document type, or "no fit", who the document is for, whether you fitted the file or the person corrected you, and the request or line that allowed the save. knowledge-mcp writes no file: you read and write the record with your own tools, and `kb_fit_record` merges your changes into the text you read.

## When to Save

Save the record only on one of two grounds:

- `request`: the person asked in this session, such as "record what each file in docs/ is".
- `line`: a standing line the person wrote for agents covers keeping the record, such as a line in AGENTS.md. Quote the line and say where the line sits.

Send the ground as `basis`, `basis_text` and `basis_location` on every call that should save. Each saved entry names the ground. Without a ground, `kb_fit_record` still says what changed, and the answer holds no text to save: tell the person what the record would gain and ask.

## The Flow

1. **First call of a session.** Read the record, or use an empty text when the file is missing. List every file of the knowledge base with its path from the top folder, and a fingerprint when you can compute one cheaply, such as `sha256:` and the SHA-256 of the content. Leave everything inside `.knowledge-bus/` out of the listing. Send the record as `record`, the files as `listing`, and every `.knowledge-bus/` folder as `universe_specs`, with the `*.kbp.yaml` files and `workspace.yaml` directly inside and nothing from `plugins/`. knowledge-mcp compares the listing with the record: moved files keep their entries, including files renamed outside this session, and deleted files leave the record. Keep the answer's `listing_changes`, the changes the listing showed, until you have written this call's record.
2. **As you work.** After you create, move or delete a file, send `changes` with the file's path, and `old_path` for a move. A rename is caught when the file keeps its content or its file name: after a rename outside this session that also changed the content, a deleted correction comes back with a note, so ask the person whether the file moved and send the correction again for the new path. When the record file still holds the text the last answer returned, send `record_digest` in place of the text.
3. **Settle.** Files in `to_settle` need a fit. Settle each one the way `kb_fit` asks: path, then document type from the candidates, or from `every_document_type` in the file's scope, then hat. Send the result in `fits` with `made` `fit`, or `no_fit` true when no document type fits. Ask the person only when these steps leave more than one fit. Add `audience` when you know who the document is for: `confirmed` once the person confirmed the value, else `guessed`.
4. **Corrections.** When the person says a file is another document type, fits nowhere, or is for someone else, send the change in `fits` with `made` `correction`, and the person's words as a `request` ground. A correction wins over any later fit, and moves with its file.
5. **Write.** When the answer's `record` holds text, read the record file again right before writing. If the file still holds the text you sent, write the returned text at once. If the file changed, another chat saved meanwhile: send the new text with the same `changes` and `fits`, and no `listing`. Only when the call that merges again is the call that carried the listing, add that answer's `listing_changes` to `changes`; every later call re-sends its own `changes` and `fits` only. Compared with the newer text, the earlier listing would drop the other chat's new files and bring back the files the other chat deleted. Then write the text of the second answer. Leave the file alone when `record` is empty.
6. **Re-index.** When the person asks to check every file again, send `refit` true and settle the files in `to_settle`. Corrections stay out of the list.

## Using the Record

Send the record's text to `kb_fit` as `record`, or its digest as `record_digest`. `kb_fit` answers a recorded file from the record, labelled "from the record", including "no fit". Use the recorded fit and reader, and say the answer came from the record.

## Never

Write no other file for the record, and change no entry by hand in the record file. The record holds paths, fits and fingerprints, and holds no document text.
