// One "Every surface" frame per flow: the app card, both text cards, MCP, CLI and API, each marked as shipped, gap or proposed.
// Where the card renders, from support.claude.com/en/articles/13454812 and the MCP Apps quickstart.
window.KMHOSTS =
  "<b>Renders the card:</b> Claude web, Claude Desktop, Claude for iOS and Android, Cowork. <b>Text only:</b> Claude Code (“calls the tool as text and doesn’t render the UI”; the model gets structuredContent as a JSON string). <b>Other hosts:</b> not verified.";
window.SURF = (() => {
  const K = window.KM,
    X = window.KMTEXT;
  const esc = (s) =>
    s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  // Just enough Markdown for knowledge-mcp's text cards: code spans, bold, tables, list items, paragraphs.
  const inline = (s) =>
    esc(s)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>");
  const md = (src) => {
    const out = [];
    const lines = src.split("\n");
    let i = 0;
    while (i < lines.length) {
      const l = lines[i];
      if (l.startsWith("|")) {
        const rows = [];
        while (i < lines.length && lines[i].startsWith("|")) {
          rows.push(lines[i]);
          i++;
        }
        const cells = (r) =>
          r
            .slice(1, -1)
            .split(" | ")
            .map((c) => c.trim());
        out.push(
          `<table class="mdt"><tr>${cells(rows[0])
            .map((c) => `<th>${inline(c)}</th>`)
            .join("")}</tr>${rows
            .slice(2)
            .map(
              (r) =>
                `<tr>${cells(r)
                  .map((c) => `<td>${inline(c)}</td>`)
                  .join("")}</tr>`,
            )
            .join("")}</table>`,
        );
        continue;
      }
      if (l.startsWith("- ")) {
        const it = [];
        while (i < lines.length && lines[i].startsWith("- ")) {
          it.push(`<li>${inline(lines[i].slice(2))}</li>`);
          i++;
        }
        out.push(`<ul>${it.join("")}</ul>`);
        continue;
      }
      if (l.trim()) out.push(`<p>${inline(l)}</p>`);
      i++;
    }
    return out.join("");
  };
  const pre = (s) => `<pre>${esc(s)}</pre>`;
  const st = {
    shipped: ["b-grn", "Shipped in 0.4.0"],
    gap: ["b-amb", "Gap: not built"],
    proposed: ["b-blu", "Proposed here"],
    none: ["b-nt", "Does not exist"],
  };
  const tag = (k) => K.badge(st[k][0], st[k][1]);
  const block = (n, title, status, body) =>
    `<div class="blk"><div class="bh"><span class="bn">${n}</span><b>${title}</b>${tag(status)}</div>${body}</div>`;
  const api = block(
    6,
    "API",
    "none",
    '<p>No HTTP API. Neither knowledge-mcp nor knowledge-bus runs a server: knowledge-mcp speaks MCP over stdin and stdout (<code>kb mcp</code>), and knowledge-bus ships the <code>kbp</code> checker and skills.</p><p class="mu">Checked in both repos: no server framework in runtime/knowledge_mcp or checker/.</p>',
  );
  const jsonOnly = (tools) =>
    `<p>The host gets the tool’s JSON as text and structuredContent; there is no Markdown card for ${tools}. The assistant writes its own summary, so wording drifts from the app.</p>`;

  const flows = {
    "p01-orientation": {
      name: "Orientation",
      frames: "O01–O04",
      ui: [
        "proposed",
        "<p>A card drawn from <code>kb_prepare_document_types</code>. Its last-change row needs <code>kb_list_edits</code> too: one card cannot draw from two tool results (open ruling).</p>",
      ],
      chat: [
        "gap",
        jsonOnly("document types") +
          `<p class="mu">kb_list_edits does have one, for the latest edit only:</p><div class="md">${md(X.pickup)}</div>`,
      ],
      term: [
        "gap",
        `<p>Same as chat. The latest-edit card, as a terminal prints it:</p>${pre(X.pickup)}`,
      ],
      mcp: [
        "shipped",
        "<p><code>kb_prepare_document_types</code> → <code>knowledge-mcp/document-types-update/1</code><br><code>kb_list_edits</code> → <code>knowledge-mcp/edits/2</code></p>",
      ],
      cli: [
        "shipped",
        `<p><code>kb kbp kinds</code> lists the document types in scope (JSON):</p>${pre(X.cli_kinds)}<p class="mu">No CLI command reports new or moved files.</p>`,
      ],
    },
    "p02-document": {
      name: "Document",
      frames: "D01–D06, D05F",
      ui: [
        "proposed",
        "<p>D01–D04 from <code>kb_get_document_type</code>; D05–D06 from <code>kb_prepare_proposal</code> rows as additions.</p>",
      ],
      chat: [
        "gap",
        jsonOnly("document types or readers") +
          '<p class="mu">D05 (new document) reuses the proposal card below in flow 03.</p>',
      ],
      term: ["gap", "<p>Same as chat.</p>"],
      mcp: [
        "shipped",
        "<p><code>kb_get_document_type</code> → <code>knowledge-mcp/document-type/1</code><br><code>kbp_card</code> → <code>knowledge-mcp/kbp-output/1</code><br><code>kb_list_audiences</code> → <code>knowledge-mcp/audiences/1</code><br><code>kb_prepare_proposal</code> → <code>knowledge-mcp/proposal/1</code></p>",
      ],
      cli: [
        "shipped",
        `<p><code>kb type &lt;path&gt; --role maintainer</code> (excerpt; columns TYPE SPEC MATCHED-BY USED-BY PROPOSED-FOLDER PROPOSED-NAME TITLE):</p>${pre(X.cli_type)}<p><code>kb kbp card design-doc --format markdown</code> (first lines):</p>${pre(X.cli_card)}`,
      ],
    },
    "p03-evidence": {
      name: "Evidence review",
      frames: "E01–E08, E02F",
      ui: [
        "proposed",
        "<p>The proposal card (P02) drawn from <code>kb_prepare_proposal</code>; the same rows, numbers, marks and left-out files as the text cards beside it.</p>",
      ],
      chat: [
        "shipped",
        `<p><code>layout: "table"</code>, returned in <code>structuredContent.card</code> and as the first text block:</p><div class="md">${md(X.table)}</div>`,
      ],
      term: [
        "shipped",
        `<p><code>layout: "list"</code>, for terminals, “which can’t scroll a wide table sideways”:</p>${pre(X.list)}`,
      ],
      mcp: [
        "shipped",
        '<p><code>kb_prepare_import</code> → <code>knowledge-mcp/import/1</code> (one call per source)<br><code>kb_prepare_proposal</code> → <code>knowledge-mcp/proposal/1</code> (rows = C1…Cn, left_out per file, card)</p><p class="mu">Gap: no digest in the proposal, so “changed since preview” rests on rereading the text.</p>',
      ],
      cli: ["none", "<p>No CLI command prepares a proposal.</p>"],
    },
    "p04-edit-result": {
      name: "Edit result",
      frames: "R01–R04",
      ui: [
        "proposed",
        "<p>Result card drawn from <code>kb_record_edit</code>; the undo refusal from <code>kb_list_edits</code>.</p>",
      ],
      chat: [
        "shipped",
        `<div class="md">${md(X.saved)}</div><p class="mu">Copy differs from the app (“cache-proposal.md · 4 changes”): one copy source must serve both.</p>`,
      ],
      term: ["shipped", pre(X.saved)],
      mcp: [
        "shipped",
        '<p><code>kb_record_edit</code> → <code>knowledge-mcp/edit/2</code> (before/after digests)<br><code>kb_list_edits</code> → <code>knowledge-mcp/edits/2</code></p><p class="mu">No undo tool: the assistant restores and records the undo as a new edit.</p>',
      ],
      cli: ["none", "<p>No CLI command records, lists or undoes edits.</p>"],
    },
    "p05-move-plan": {
      name: "Move plan",
      frames: "M01–M06, M05F",
      ui: [
        "proposed",
        "<p>Plan card drawn from <code>kb_prepare_document_moves</code>; result from the last <code>kb_record_edit</code> of the operation.</p>",
      ],
      chat: ["gap", jsonOnly("move plans")],
      term: ["gap", "<p>Same as chat.</p>"],
      mcp: [
        "shipped",
        "<p><code>kb_prepare_document_moves</code> → <code>knowledge-mcp/document-moves/1</code><br><code>kb_prepare_document_move</code> → <code>knowledge-mcp/document-move/1</code><br><code>kb_record_edit</code> → <code>knowledge-mcp/edit/2</code> (operation index and count)</p>",
      ],
      cli: [
        "shipped",
        "<p><code>kb type &lt;path&gt;</code> shows PROPOSED-FOLDER and PROPOSED-NAME for one file (<code>&lt;none&gt;</code> without a convention). No CLI command moves files.</p>",
      ],
    },
    "p06-conventions": {
      name: "Conventions",
      frames: "C01–C03, C01F",
      ui: [
        "proposed",
        "<p>Decision rows (P04) drawn from <code>kb_prepare_conventions</code>.</p>",
      ],
      chat: ["gap", jsonOnly("conventions")],
      term: ["gap", "<p>Same as chat.</p>"],
      mcp: [
        "shipped",
        "<p><code>kb_list_convention_templates</code> → <code>knowledge-mcp/convention-templates/1</code><br><code>kb_prepare_conventions</code> → <code>knowledge-mcp/conventions-update/1</code><br><code>kb_list_conventions</code> → <code>knowledge-mcp/folder-conventions/1</code></p>",
      ],
      cli: [
        "shipped",
        "<p><code>kb type --filing-values …</code> previews a name under saved conventions. No CLI command proposes or saves them.</p>",
      ],
    },
    "p07-history": {
      name: "History",
      frames: "H01–H02, H01F",
      ui: [
        "proposed",
        "<p>History card drawn from <code>kb_list_edits</code>.</p>",
      ],
      chat: [
        "gap",
        `<p>Only the latest edit has a card today:</p><div class="md">${md(X.pickup)}</div><p class="mu">The full list is JSON only.</p>`,
      ],
      term: ["gap", pre(X.pickup)],
      mcp: [
        "shipped",
        "<p><code>kb_list_edits</code> → <code>knowledge-mcp/edits/2</code></p>",
      ],
      cli: ["none", "<p>No CLI command lists edits.</p>"],
    },
    "p08-guidance": {
      name: "Guidance change",
      frames: "G01–G03, G01F",
      ui: [
        "proposed",
        "<p>No tool draws the change table: it comes from the kb-evolve skill (open ruling). G02–G03 can hang on <code>kbp_validate</code>.</p>",
      ],
      chat: [
        "gap",
        "<p>The skill’s change table is the assistant’s own Markdown, not a server card.</p>",
      ],
      term: ["gap", "<p>Same as chat.</p>"],
      mcp: [
        "shipped",
        "<p><code>kbp_validate</code> → <code>knowledge-mcp/kbp-output/1</code></p>",
      ],
      cli: [
        "shipped",
        `<p><code>kb kbp validate</code>, on the bundled product-development guidance:</p>${pre(X.cli_validate)}`,
      ],
    },
  };

  const css = `body{width:1440px}.wrap{padding:40px 56px}
.sid{font:600 12px/1 var(--font-mono);color:var(--color-text-tertiary)}.sn{font-size:22px;line-height:28px;font-weight:600;margin-top:6px}.sp2{color:var(--color-text-tertiary);margin-top:6px;max-width:980px}
.hosts{margin-top:14px;font-size:12px;color:var(--color-text-tertiary)}
.g{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:22px}
.blk{border:1px solid var(--color-border-tertiary);border-radius:14px;background:var(--color-background-primary);padding:14px 16px;font-size:12.5px;line-height:18px;min-width:0}
.bh{display:flex;align-items:center;gap:8px;margin-bottom:10px}.bh b{flex:1}.bn{font:600 11px/1 var(--font-mono);color:var(--color-text-tertiary)}
.blk p{margin:0 0 8px}.blk code{font-family:var(--font-mono);font-size:11.5px;background:var(--color-background-secondary);border-radius:4px;padding:0 4px}
pre{font:11px/16px var(--font-mono);background:var(--color-background-secondary);border-radius:10px;padding:10px 12px;white-space:pre-wrap;word-break:break-word;margin:0 0 8px}
.md{border:1px dashed var(--color-border-secondary);border-radius:10px;padding:10px 12px;margin-bottom:8px}.md p{margin:0 0 6px}.md ul{margin:0 0 6px 16px}
.mdt{border-collapse:collapse;width:100%;font-size:11.5px;margin:4px 0 8px}.mdt th,.mdt td{border:1px solid var(--color-border-tertiary);padding:4px 6px;text-align:left;vertical-align:top}.mdt th{color:var(--color-text-tertiary);font-weight:500}`;
  const html = (theme, pg) => {
    const f = flows[pg];
    const hosts = window.KMHOSTS
      ? `<div class="hosts">${window.KMHOSTS}</div>`
      : "";
    return `<!doctype html><html><head><meta charset="utf-8"><style>${K.css}${css}</style></head><body class="${theme}"><div class="wrap"><div class="sid">${f.frames} · every surface</div><div class="sn">${f.name}: one flow, six surfaces</div><div class="sp2">The same flow as each surface delivers it. Text cards and CLI output are real output from knowledge-mcp 0.4.0, run on this storyboard’s data; nothing is mocked. “Gap” marks what has to be built for the fallback to match the app.</div>${hosts}<div class="g">${block(1, "MCP App card", f.ui[0], f.ui[1] + `<p class="mu">Frames ${f.frames} on this page.</p>`)}${block(2, "Text card · chat without Apps", f.chat[0], f.chat[1])}${block(3, "Text card · terminal (Claude Code)", f.term[0], f.term[1])}${block(4, "MCP tools", f.mcp[0], f.mcp[1])}${block(5, "CLI", f.cli[0], f.cli[1])}${api}</div></div></body></html>`;
  };
  return { flows, html };
})();
("ok");
