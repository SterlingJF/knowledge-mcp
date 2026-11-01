# MCP App cards

One card per slice. Each card lists the frames it builds, the files it owns, when it is done, and what blocks it. A card is done when it matches its frames in light and dark, its lanes pass, and both reviewers ([reuse](reviewers/reuse.md), [polish](reviewers/polish.md)) pass.

## Batch 0: foundations (coordinator)

- [x] **0.1 Scaffold** `mcp-app/` package: Vite, React, Tailwind, shadcn core, Vitest, single-file build; module wiring (README layout, `check_mcp_app`, CI job, CONTRIBUTING map). Blocks everything.
- [x] **0.2 Tokens and copy:** `src/generated/tokens.auto.css` from `kmtokens.js` with a staleness check; `src/copy/en.ts` from F07. Blocks every element.
- [x] **0.3 Host bridge:** connect, host styles and fonts, transparent ground, display modes, size changes, `ui/message`; a card router on `structuredContent.schema`. Blocks every card.

## Batch 1: elements and engine (workers)

- [x] **K-A Status and actions:** K01 Badge, K02 Button, K11 Segmented choice, K13 Full view button. Owns `component-elements/{badge,button,segmented-choice,full-view-button}.tsx`. Blocked by 0.1, 0.2.
- [x] **K-B Evidence and sources:** K03 Evidence mark, K04 Chips, K05 Change number and tick box (with select-all), K06 Note. Owns `component-elements/{evidence-mark,chips,change-number,note}.tsx`. Blocked by 0.1, 0.2.
- [x] **K-C Text and loading:** K07 Text lines, K08 Key–value grid (refuses more than 5 rows), K09 Diff, K10 Skeleton. Owns `component-elements/{text-lines,key-value,diff,skeleton}.tsx`. Blocked by 0.1, 0.2.
- [x] **E1 Apps registration:** `mcp.server.apps` resource `ui://knowledge-mcp/app.html`, `_meta.ui.resourceUri` and `prefersBorder: true` on UI tools, CSP for `https://assets.claude.ai`, built HTML shipped in the runtime with a staleness check. Owns `runtime/knowledge_mcp/apps.py`, its tests. Blocked by 0.1.

## Batch 2: patterns and the first card

- [x] **P-A Card frame:** P01 Card shell (live, frozen, replaced; flat inside the full view), P05 Result and refusal, P06 Card lifecycle (freeze on press, send the message, stand down when a newer card about the same file exists), P07 Summary and full view. Owns `component-patterns/{card-shell,result-card,card-lifecycle,summary-card,full-view}.*`. Blocked by batch 1.
- [x] **P-B Card bodies:** P02 Change table (Cn rows, tick boxes, select-all, frozen, stacked under 560px), P03 Left-out disclosure (closed and open), P04 Decision rows (segmented choice per row, decided badges). Owns `component-patterns/{change-table,left-out,decision-rows}.*`. Blocked by batch 1.
- [x] **E2+E3 Proposal contract:** a `based_on` digest of the document the proposal was prepared against, and a supersession key (`subject`, `created_at`, `seq`) in the `kb_prepare_proposal` result. Owns `contracts/extensions/mcp/v1/proposal.schema.yaml`, its samples, the generated models, `runtime/knowledge_mcp/tools/proposal.py` and its tests. The coordinator updates `mcp-app/src/contracts/proposal.ts`.
- [x] **C-Proposal** E01–E08, E02F, D05, D05F on `kb_prepare_proposal`. Blocked by P-A, P-B, E2+E3.

- [x] **H1 Local host harness:** a dev page that hosts the built app the way Claude does (ext-apps AppBridge, sandboxed iframe, Claude's style variables, light and dark, inline and fullscreen), feeds it a real `kb_prepare_proposal` result, and records every ui/message and model context. Owns `mcp-app/harness.html`, `mcp-app/src/harness/*`. Blocked by batch 1.

- [x] **E5 Proposal document type and reader:** the E-frames show "Design proposal · for maintainers deciding whether to accept it" after the file chip, but `knowledge-mcp/proposal/1` has no field for it. Add optional `document_type` and `reader` (the assistant has both from `kb_get_document_type`), then the card shows them. Contract change. The same contract change also covers three more gaps found while building C-Proposal: the naming-rule note after "Saved as" (D05 "· no naming rule", the D05F panel); an open question with no source (D05 "Needs you · Rollout owner · no source", the D05F "One thing to answer" panel), since proposal/1 has no open questions apart from conflicting rows; and a source that is a whole file with no line or place (D05F "vendor-quote.xlsx").

## Batch 3: results and moves

- [x] **C-Result** R01–R04, D06 on `kb_record_edit`, `kb_list_edits`. Blocked by P-A, P-B.
- [x] **C-Move** M01–M06, M05F on `kb_prepare_document_moves`. Blocked by P-A, P-B.
- [x] **E4 Text cards for move plans and conventions** (spec MUST), sharing copy with the app.
- [x] **E6 Edit result contract:** the changed lines (capped) and a change count for R01–R02, a created flag for D06, the undone edit's id for R03. Owns `edit.schema.yaml`, `tools/edits.py`, the `saved` view.
- [x] **E7 Move plan contract:** a title, files that stay and why, the naming rule behind each rename, the source summary, and blocker choices where the tool can compute them (M01, M02, M05, M05F). Owns `document-moves.schema.yaml`, `tools/document_moves.py`.
- [x] **K14 Tabs and P08 Plan table:** tabs with counts and a read-only table with given columns and "+ N more", for M02 and M05F. Owns `component-elements/tabs.*`, `component-core/tabs.tsx`, `component-patterns/plan-table.*`.
- [ ] **E8 Link details in move plans:** each link repair carries its line number and the original link text, so M02 can show `decisions-index.md:12` and `[[retire-evening]]` rather than a path. Owns `document-moves.schema.yaml`, `document_move.py`.
- [x] **S1 Spacing pass:** spacing roles, narrow cards by container, whole file names, touch targets. **P05 disclosure**, **K11 adaptive choice**, **P04 per-row options**, **K15 Link button**.
- [ ] **Bind the new cards:** add `kb_record_edit` and `kb_prepare_document_moves` to `apps.py` TOOLS. Waits on the live check below: both tools return results the cards deliberately draw nothing for (`texts_needed`, `unchanged`, the middle writes of a grouped move), and how Claude shows an app that draws nothing is not verified.
- [ ] **M04 grouped writes:** a move ends in N `kb_record_edit` receipts sharing an `operation`; one card should stand for the operation (on its last write, "N of N writes recorded · every link checked"), the others draw nothing.
- Live check 11-01: the proposal card renders in a Claude Desktop chat with no folder attached. With a folder attached (Cowork-style), the same server call drew only text and no iframe. Without a nudge, Cowork skipped knowledge-mcp and edited the file directly.
- [ ] **No double card:** with the app drawn, Claude also repeats the Markdown card below it, because the tool description says to show `card` unchanged. Needs wording that works for hosts with and without apps.
- [ ] **Live check in Claude:** register knowledge-mcp with Claude Desktop and run the proposal, edit and move flows; confirm theming, fullscreen, ui/message, model context, stand-down, and what an empty app shows. Needs Sterling's OK (changes his Claude setup).
- Open: an undo's `undoes` is in the receipt only, not in edits.jsonl, so `kb_list_edits` can't show which edit undid which, and pickup could offer to undo an undo. Storing it changes the stored file: edits/3.
- Open: R04 (undo no longer safe) is the assistant's check against `kb_list_edits`; no tool result draws it yet. M04 (moved, links checked) is the result of the assistant's `kb_record_edit` writes, so C-Result draws it once E6 lands.

## Batch 4: the rest

- [ ] **C-Conventions** C01–C03, C01F. **C-History** H01, H01F, H02. **C-Document** D01–D04. **C-Orientation** O01–O04 and **C-Guidance** G01–G03, G01F wait for the open rulings on which tool draws them.
- [ ] **E5–E6 Text cards** for document types, history and the rest.
- [ ] **Host checks** in Claude Desktop, Claude web, Claude for iOS, and Claude Code for the fallback.

## Open, not blocking batch 0–1

- Which tool draws Orientation (01) and Guidance change (08).
- Every card at 320px; keyboard order and screen-reader labels.
- The storyboard's sample document types are not in the bundled guidance.
