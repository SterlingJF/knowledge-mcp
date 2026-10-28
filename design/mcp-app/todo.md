# MCP App cards

One card per slice. Each card lists the frames it builds, the files it owns, when it is done, and what blocks it. A card is done when it matches its frames in light and dark, its lanes pass, and both reviewers ([reuse](reviewers/reuse.md), [polish](reviewers/polish.md)) pass.

## Batch 0: foundations (coordinator)

- [ ] **0.1 Scaffold** `mcp-app/` package: Vite, React, Tailwind, shadcn core, Vitest, single-file build; module wiring (README layout, `check_mcp_app`, CI job, CONTRIBUTING map). Blocks everything.
- [ ] **0.2 Tokens and copy:** `src/generated/tokens.auto.css` from `kmtokens.js` with a staleness check; `src/copy/en.ts` from F07. Blocks every element.
- [ ] **0.3 Host bridge:** connect, host styles and fonts, transparent ground, display modes, size changes, `ui/message`; a card router on `structuredContent.schema`. Blocks every card.

## Batch 1: elements and engine (workers)

- [ ] **K-A Status and actions:** K01 Badge, K02 Button, K11 Segmented choice, K13 Full view button. Owns `component-elements/{badge,button,segmented-choice,full-view-button}.tsx`. Blocked by 0.1, 0.2.
- [ ] **K-B Evidence and sources:** K03 Evidence mark, K04 Chips, K05 Change number and tick box (with select-all), K06 Note. Owns `component-elements/{evidence-mark,chips,change-number,note}.tsx`. Blocked by 0.1, 0.2.
- [ ] **K-C Text and loading:** K07 Text lines, K08 Key–value grid (refuses more than 5 rows), K09 Diff, K10 Skeleton. Owns `component-elements/{text-lines,key-value,diff,skeleton}.tsx`. Blocked by 0.1, 0.2.
- [ ] **E1 Apps registration:** `mcp.server.apps` resource `ui://knowledge-mcp/app.html`, `_meta.ui.resourceUri` and `prefersBorder: true` on UI tools, CSP for `https://assets.claude.ai`, built HTML shipped in the runtime with a staleness check. Owns `runtime/knowledge_mcp/apps.py`, its tests. Blocked by 0.1.

## Batch 2: patterns and the first card

- [ ] **P-A** P01 Card shell, P06 Card lifecycle (freeze, send, replaced), P07 Summary and full view. Blocked by K-A, K-C, 0.3.
- [ ] **P-B** P02 Change table, P03 Left-out disclosure, P04 Decision rows, P05 Result and refusal. Blocked by K-A, K-B, K-C.
- [ ] **E2 Proposal digest:** `based_on` digest in `knowledge-mcp/proposal/1` so “changed since preview” rests on a digest. Contract change; coordinator merges.
- [ ] **E3 Supersession key:** `{createdAt, seq}` in every UI tool result. Contract change. Blocks P06 “Replaced”.
- [ ] **C-Proposal** E01–E08, E02F, D05, D05F on `kb_prepare_proposal`. Blocked by P-A, P-B, E1.

## Batch 3: results and moves

- [ ] **C-Result** R01–R04, D06 on `kb_record_edit`, `kb_list_edits`. Blocked by P-A, P-B.
- [ ] **C-Move** M01–M06, M05F on `kb_prepare_document_moves`. Blocked by P-A, P-B.
- [ ] **E4 Text cards for move plans and conventions** (spec MUST), sharing copy with the app.

## Batch 4: the rest

- [ ] **C-Conventions** C01–C03, C01F. **C-History** H01, H01F, H02. **C-Document** D01–D04. **C-Orientation** O01–O04 and **C-Guidance** G01–G03, G01F wait for the open rulings on which tool draws them.
- [ ] **E5–E6 Text cards** for document types, history and the rest.
- [ ] **Host checks** in Claude Desktop, Claude web, Claude for iOS, and Claude Code for the fallback.

## Open, not blocking batch 0–1

- Which tool draws Orientation (01) and Guidance change (08).
- Every card at 320px; keyboard order and screen-reader labels.
- The storyboard's sample document types are not in the bundled guidance.
