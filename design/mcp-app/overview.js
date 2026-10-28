// 00 Overview: every card, state and branch, plus how to read the storyboard.
window.OVERVIEW = (theme) => {
  const K = window.KM;
  const flows = [
    [
      "01",
      "Orientation",
      "Get oriented in a folder",
      [
        ["O01", "Reading"],
        ["O02", "Oriented"],
      ],
      [
        ["O03", "No guidance yet"],
        ["O04", "Guidance has problems"],
      ],
    ],
    [
      "02",
      "Document",
      "Know a document, or write a new one",
      [
        ["D01", "Type, reader, checks"],
        "|",
        ["D05", "New: summary"],
        ["D06", "Created"],
      ],
      [
        ["D05F", "⤢ Each section"],
        ["D02", "Two types fit"],
        ["D03", "No type"],
        ["D04", "Reader is a guess"],
      ],
    ],
    [
      "03",
      "Evidence review",
      "Bring sources into a document",
      [
        ["E01", "Reading sources"],
        ["E02", "Summary"],
        ["E05", "Approved: saving"],
      ],
      [
        ["E02F", "⤢ Every change"],
        ["E08", "⤢ Change left out"],
        ["E03", "⤢ Why left out"],
        ["E04", "Said instead"],
        ["E06", "Not now"],
        ["E07", "Changed since preview"],
      ],
    ],
    [
      "04",
      "Edit result",
      "See and undo what was saved",
      [
        ["R01", "Saved"],
        ["R03", "Undone"],
      ],
      [
        ["R02", "Change opened"],
        ["R04", "Undo not safe"],
      ],
    ],
    [
      "05",
      "Move plan",
      "File and rename, links intact",
      [
        ["M01", "Summary"],
        ["M03", "Moving"],
        ["M04", "Moved, links checked"],
      ],
      [
        ["M02", "⤢ Moves and links"],
        ["M05", "Blockers"],
        ["M05F", "⤢ Answer blockers"],
        ["M06", "Not now"],
      ],
    ],
    [
      "06",
      "Conventions",
      "Agree naming rules",
      [
        ["C01", "Summary"],
        ["C03", "Saved"],
      ],
      [
        ["C01F", "⤢ Accept or drop"],
        ["C02", "Row changed in chat"],
      ],
    ],
    [
      "07",
      "History",
      "Who changed what, for whom",
      [["H01", "Summary"]],
      [
        ["H01F", "⤢ Every change"],
        ["H02", "Nothing yet"],
      ],
    ],
    [
      "08",
      "Guidance change",
      "Improve guidance from evidence",
      [
        ["G01", "Summary"],
        ["G02", "Applied"],
      ],
      [
        ["G01F", "⤢ Change table"],
        ["G03", "Checker refused"],
      ],
    ],
  ];
  const st = (id, t, cls) => `<span class="st ${cls}"><b>${id}</b>${t}</span>`;
  const rows = flows
    .map(
      ([n, name, job, main, br]) =>
        `<tr><td><div class="fn">${n}</div></td><td><div class="tt">${name}</div><div class="mu">${job}</div></td><td><div class="path">${main
          .map((x) =>
            x === "|" ? '<span class="brk"></span>' : st(x[0], x[1], "m"),
          )
          .join('<span class="ar">→</span>')
          .replace(
            /<span class="ar">→<\/span><span class="brk"><\/span><span class="ar">→<\/span>/g,
            '<span class="brk"></span>',
          )}</div></td><td><div class="path">${br.map(([i, t]) => st(i, t, "b")).join("")}</div></td></tr>`,
    )
    .join("");
  const recs = [
    "Inline cards in the host chat. A dense card shows a summary inline (at most 5 data points, 2 actions) and its full table in the full view (amended Oct 28). The host draws the chat, steps and composer.",
    "Buttons send the assistant the exact preview (the C-numbers and the text they replace); it rechecks the file before writing.",
    "Every write waits for your OK (a request, instruction or accepted change) and is recorded.",
    "Every result card offers Undo, as its own recorded change, only where the file still matches.",
    "What was left out is always listed, with a reason per item.",
    "Progress shows only inside one call; no background-job cards.",
  ];
  const css =
    K.css +
    `
body{width:1600px}.wrap{padding:40px 56px}
h1{font-size:22px;font-weight:600}.sub{color:var(--color-text-tertiary);margin-top:4px;font-size:13px}
.cols{display:grid;grid-template-columns:1fr 420px;gap:36px;margin-top:26px}
table.map{width:100%;border-collapse:collapse}
.map th{font-weight:500;color:var(--color-text-tertiary);font-size:11px;letter-spacing:.06em;text-transform:uppercase;text-align:left;padding:0 10px 8px 0;border-bottom:1px solid var(--color-border-tertiary)}
.map td{padding:12px 10px 12px 0;border-bottom:1px solid var(--color-border-tertiary);vertical-align:top}
.fn{font:600 12px/1 var(--font-mono);color:var(--color-text-tertiary);padding-top:3px}
.path{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.st{display:inline-flex;gap:6px;align-items:center;border-radius:8px;padding:4px 9px;font-size:12px;white-space:nowrap}
.st b{font:600 11px/1 var(--font-mono)}
.st.m{background:var(--color-background-primary);border:1px solid var(--color-border-secondary)}
.st.b{border:1px dashed var(--color-border-secondary);color:var(--color-text-tertiary)}
.ar{color:var(--color-text-tertiary)}.brk{flex-basis:100%;height:0}
.box{border:1px solid var(--color-border-tertiary);border-radius:14px;background:var(--color-background-primary);padding:16px 18px;margin-bottom:16px}
.box h2{font-size:11px;letter-spacing:.07em;text-transform:uppercase;color:var(--color-text-tertiary);font-weight:600;margin-bottom:10px}
.box li{margin:0 0 7px 18px;font-size:12.5px}
.lg{display:grid;grid-template-columns:auto 1fr;gap:8px 12px;align-items:center;font-size:12.5px}.lg>*:nth-child(odd){justify-self:start}`;
  const legend = `<div class="lg">${st("E02", "State", "m")}<span>Main path, left to right</span>${st("E06", "Branch", "b")}<span>Off the main path: a choice, an empty state or a refusal</span>
${K.badge("b-amb", "Needs your OK")}<span>Waiting for you; nothing written yet</span>
<span class="badge b-grn">${K.ic.check}Saved</span><span>Written and recorded; Undo offered</span>
<span class="badge b-red">${K.ic.warn}Can’t undo safely</span><span>Refused, with the reason; nothing written</span>
<span class="badge b-nt">Not saved</span><span>Declined or frozen; history only</span></div>`;
  const how = `<ul><li>Each page holds one flow. Light frames on the left, the same frames in dark 3,400 px to the right.</li><li>Inside each frame, the dashed box is the host chat (Claude, ChatGPT or Codex). Only the solid cards are the app.</li><li>The strip under each frame says what the user does, what they see, what the system does, and the evidence behind it: TheDriveAI frame IDs on the Competitor UI References canvas, and knowledge-mcp docs and skills.</li><li><b>Build from the 00 pages.</b> Foundations, Components and Patterns hold every token, part and rule. Every frame here is drawn from the same tokens; a part not on those pages doesn’t exist yet.</li><li><b>Buttons never write.</b> A press freezes the card and sends a message, shown as “Sent from the card”. The assistant does the work, and the outcome arrives as a new card. A card never changes after it is drawn.</li><li>All frames use one fictional folder, Build Operations, so the flows read as one session.</li></ul>`;
  return `<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head><body class="${theme}"><div class="wrap"><h1>knowledge-mcp · MCP App storyboard</h1><div class="sub">8 flows · ${flows.reduce((n, f) => n + f[3].filter((x) => x !== "|").length + f[4].length, 0)} states · light and dark · for walkthrough before components and tokens</div>
<div class="cols"><div><table class="map"><tr><th></th><th>Flow</th><th>Main path</th><th>Branches</th></tr>${rows}</table></div>
<div><div class="box"><h2>How to read this</h2>${how}</div><div class="box"><h2>Legend</h2>${legend}</div><div class="box"><h2>Approved recommendations</h2><ol>${recs.map((r) => `<li>${r}</li>`).join("")}</ol></div></div></div></div></body></html>`;
};
("ok");
