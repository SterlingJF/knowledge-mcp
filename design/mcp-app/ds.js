// Design-system sheets: Foundations, Components (elements) and Patterns, all drawn from kmtokens.js through kmgen.js.
window.DS = (() => {
  const K = window.KM,
    T = window.KMT,
    { ic, chip, src, evTag, badge, btn, card } = K;

  // Contrast, so every text colour is checked against the surface it sits on.
  const rgb = (c) =>
    c.startsWith("#")
      ? [[1, 3, 5].map((k) => parseInt(c.slice(k, k + 2), 16)), 1]
      : ((m) => [m.slice(0, 3).map(Number), Number(m[3])])(c.match(/[\d.]+/g));
  const solid = (c, bg) => {
    const [f, a] = rgb(c),
      [b] = rgb(bg);
    return f.map((v, k) => v * a + b[k] * (1 - a));
  };
  const lum = (p) => {
    const c = p
      .map((v) => v / 255)
      .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  };
  const ratio = (fg, bg) => {
    const [x, y] = [lum(solid(fg, bg)), lum(rgb(bg)[0])].sort((p, q) => q - p);
    return (x + 0.05) / (y + 0.05);
  };
  const cr = (fg, bg, min = 4.5) => {
    const r = ratio(fg, bg);
    return `<span class="crt ${r >= min ? "ok" : "no"}">${r.toFixed(1)}${r >= min ? " ✓" : " ✕"}</span>`;
  };

  // The light pane pins light values, so one frame shows both themes whatever the frame's own theme.
  const lightVars = Object.entries(T.color.light)
    .map(([k, v]) => `${k}:${v}`)
    .join(";");
  const css = `
.lt{${lightVars};color-scheme:light}
body{width:1440px}.sheet{padding:40px 56px 36px}
.sh{display:flex;justify-content:space-between;align-items:flex-start;gap:24px;border-bottom:1px solid var(--color-border-tertiary);padding-bottom:18px}
.sid{font:600 12px/1 var(--font-mono);color:var(--color-text-tertiary)}
.sn{font-size:22px;line-height:28px;font-weight:600;margin-top:6px}
.sp2{color:var(--color-text-tertiary);margin-top:6px;max-width:820px}
.lay{font-size:11px;letter-spacing:var(--km-eyebrow-tracking);text-transform:uppercase;font-weight:500;border:1px solid var(--color-border-secondary);border-radius:999px;padding:3px 10px;color:var(--color-text-tertiary);white-space:nowrap}
.two{display:grid;grid-template-columns:1fr 1fr;gap:0;margin-top:22px;border:1px solid var(--color-border-tertiary);border-radius:14px;overflow:hidden}
.pane{padding:22px 24px;background:var(--color-background-tertiary);color:var(--color-text-primary)}
.ptag{font:600 11px/1 var(--font-mono);color:var(--color-text-tertiary);margin-bottom:14px;text-transform:uppercase;letter-spacing:.06em}
.one{margin-top:22px}
.vr{display:grid;grid-template-columns:150px 1fr;gap:12px 16px;align-items:center}
.vl{font-size:12px;color:var(--color-text-tertiary)}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.foot{display:grid;grid-template-columns:1fr 1.4fr 1fr;gap:28px;margin-top:22px;font-size:12px;line-height:18px}
.foot h4{font-size:11px;letter-spacing:var(--km-eyebrow-tracking);text-transform:uppercase;color:var(--color-text-tertiary);font-weight:600;margin-bottom:6px}
.foot li{margin:0 0 4px 16px}.foot .mono{font-size:11.5px}
.ids{display:flex;flex-wrap:wrap;gap:4px}.ids span{font:600 11px/1 var(--font-mono);border:1px solid var(--color-border-tertiary);border-radius:6px;padding:3px 6px;background:var(--color-background-primary)}
table.spec{width:100%;border-collapse:collapse;font-size:12.5px}
.spec th{text-align:left;font-weight:500;color:var(--color-text-tertiary);font-size:11px;letter-spacing:.04em;padding:0 12px 8px 0;border-bottom:1px solid var(--color-border-tertiary)}
.spec td{padding:9px 12px 9px 0;border-bottom:1px solid var(--color-border-tertiary);vertical-align:middle}
.sw{display:inline-flex;align-items:center;gap:8px}.sw i{width:28px;height:20px;border-radius:5px;border:1px solid rgba(128,128,128,.35);display:inline-block}
.crt{font:600 11px/1 var(--font-mono);padding:3px 6px;border-radius:5px}.crt.ok{color:#1d6b38;background:#e2f4e7}.crt.no{color:#a3271b;background:#fbe4e0}
.bar{height:12px;background:var(--color-text-info);border-radius:2px;opacity:.7}
.rbox{width:64px;height:44px;border:1.5px solid var(--color-border-secondary);background:var(--color-background-primary)}
.icg{display:grid;grid-template-columns:repeat(6,1fr);gap:10px}.icg div{display:flex;flex-direction:column;align-items:center;gap:6px;padding:12px 6px;border:1px solid var(--color-border-tertiary);border-radius:10px;background:var(--color-background-primary);font-size:11px;color:var(--color-text-tertiary)}.icg svg{width:18px;height:18px;color:var(--color-text-primary)}
.ann{display:inline-grid;place-items:center;width:18px;height:18px;border-radius:50%;background:#d6336c;color:#fff;font:600 10px/1 var(--font-mono);margin:0 4px;vertical-align:middle;flex:none}
.legend li{margin:0 0 6px 0;list-style:none;display:flex;gap:8px;align-items:flex-start;font-size:12.5px}
.rows.narrow tr{display:block;border-bottom:1px solid var(--color-border-tertiary);padding:8px 0}.rows.narrow tr:first-child{display:none}.rows.narrow td{display:block;border:0;padding:3px 0}
.narrowbox{width:360px}
.flow{display:flex;align-items:stretch;gap:10px;flex-wrap:wrap}.flow .st{flex:1;min-width:190px;border:1px solid var(--color-border-secondary);border-radius:12px;padding:12px 14px;background:var(--color-background-primary);font-size:12.5px}.flow .st b{display:block;margin-bottom:4px}.flow .arr{align-self:center;color:var(--color-text-tertiary);font-size:18px}
.host-o{border:1px dashed var(--color-border-secondary);border-radius:12px;padding:12px 14px;position:relative}.host-o .lbl{position:absolute;top:-9px;left:12px;background:var(--color-background-tertiary);padding:0 6px;font-size:11px;color:var(--color-text-tertiary)}
.dt{display:grid;grid-template-columns:1fr 1fr;gap:12px}.do,.dont{border-radius:10px;padding:10px 12px;font-size:12px}.do{background:var(--color-background-success)}.dont{background:var(--color-background-danger)}.do b{color:var(--color-text-success)}.dont b{color:var(--color-text-danger)}
`;

  const two = (body) =>
    `<div class="two"><div class="pane lt"><div class="ptag">Light</div>${body}</div><div class="pane dark"><div class="ptag">Dark</div>${body}</div></div>`;
  const vr = (rows) =>
    `<div class="vr">${rows.map(([l, v]) => `<div class="vl">${l}</div><div class="row">${v}</div>`).join("")}</div>`;
  const tbl = (head, rows, cls = "spec") =>
    `<table class="${cls}"><tr>${head.map((h) => `<th>${h}</th>`).join("")}</tr>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</table>`;
  const sw = (hex) =>
    `<span class="sw"><i style="background:${hex}"></i><span class="mono">${hex}</span></span>`;
  const L = T.color.light,
    D = T.color.dark;

  // ---------- Foundations ----------
  const colourRows = T.roles
    .filter((r) => r[0].startsWith("--"))
    .map(([k, use]) => [
      `<span class="mono">${k}</span>`,
      sw(L[k]),
      sw(D[k]),
      use,
    ]);
  const status = ["warning", "success", "danger", "info"];
  const statusRows = status.map((s) => {
    const use = T.roles.find((r) => r[0] === s)[1];
    const fg = `--color-text-${s}`,
      bg = `--color-background-${s}`;
    return [
      `<span class="mono">${bg}<br>${fg}</span>`,
      `${sw(L[bg])}<br>${sw(L[fg])}`,
      `${sw(D[bg])}<br>${sw(D[fg])}`,
      `${cr(L[fg], L[bg])} ${cr(D[fg], D[bg])}`,
      use,
    ];
  });
  const textChecks = [
    [
      "Primary text on chat ground",
      cr(L["--color-text-primary"], L["--color-background-tertiary"]),
      cr(D["--color-text-primary"], D["--color-background-tertiary"]),
    ],
    [
      "Tertiary text on chat ground",
      cr(L["--color-text-tertiary"], L["--color-background-tertiary"]),
      cr(D["--color-text-tertiary"], D["--color-background-tertiary"]),
    ],
    [
      "Tertiary text on note",
      cr(L["--color-text-tertiary"], L["--color-background-secondary"]),
      cr(D["--color-text-tertiary"], D["--color-background-secondary"]),
    ],
    [
      "Primary button text",
      cr(L["--color-text-inverse"], L["--color-background-inverse"]),
      cr(D["--color-text-inverse"], D["--color-background-inverse"]),
    ],
    [
      "Focus ring on chat ground (3:1)",
      cr(L["--color-ring-primary"], L["--color-background-tertiary"], 3),
      cr(D["--color-ring-primary"], D["--color-background-tertiary"], 3),
    ],
    [
      "Unticked box edge (3:1, non-text)",
      cr(L["--color-border-secondary"], L["--color-background-tertiary"], 3),
      cr(D["--color-border-secondary"], D["--color-background-tertiary"], 3),
    ],
  ];
  const typeRows = T.type.map(([tok, w, use, sample]) => [
    `<span class="mono">${tok}-size / -line-height</span><br><span class="mu">${T.font[tok + "-size"]} / ${T.font[tok + "-line-height"]} · ${w}</span>`,
    `<span style="font-size:var(${tok}-size);line-height:var(${tok}-line-height);font-weight:var(--font-weight-${w});${tok === "--font-text-xs" && sample === sample.toUpperCase() ? "letter-spacing:var(--km-eyebrow-tracking)" : ""}">${sample}</span>`,
    use,
  ]);
  const icons = [
    ["folder", "Scope, folder path"],
    ["file", "File chip, line source"],
    ["book", "Place source (slide, sheet)"],
    ["note", "Person source, Add a note"],
    ["check", "Done badge, tick box"],
    ["ok", "Supported, finished step"],
    ["partly", "Partly answered"],
    ["conflict", "Conflicting"],
    ["suggest", "Suggested"],
    ["left", "Left out, no type"],
    ["info", "Information note"],
    ["warn", "Refused, changed"],
    ["undo", "Undo"],
    ["move", "Move"],
    ["link", "Links"],
    ["clock", "Time (reserved)"],
    ["x", "Close (reserved)"],
    ["chev", "Disclosure, sent marker"],
  ];

  const terms = [
    [
      "document type",
      "kind, artifact type",
      "Guides use it 43 times; “kind” only in passing.",
    ],
    [
      "reader",
      "audience",
      "Guides say reader; kb_list_audiences keeps its tool name.",
    ],
    [
      "guidance",
      "universe spec, definitions",
      "“Universe spec” appears only in tool tables.",
    ],
    ["convention", "rule, pattern", "Used 128 times in the guides."],
    [
      "proposed changes · change C1",
      "diff, patch, suggestion",
      "proposal.schema.yaml names row n “Cn”.",
    ],
    [
      "left out",
      "ignored, skipped, excluded",
      "proposal left_out: files read but not cited.",
    ],
    [
      "saved · recorded",
      "committed, persisted, synced",
      "kb_record_edit records what was saved.",
    ],
  ];
  const labels = [
    [
      "Waiting on you",
      badge("b-amb", "Needs your OK") +
        badge("b-amb", "Nothing saved") +
        badge("b-amb", "Your choice") +
        badge("b-amb", "Needs your choice"),
    ],
    [
      "Done",
      badge("b-grn", "Saved", "check") +
        badge("b-grn", "Approved", "check") +
        badge("b-grn", "Created", "check") +
        badge("b-grn", "Moved", "check") +
        badge("b-grn", "Applied", "check") +
        badge("b-grn", "Undone", "check"),
    ],
    [
      "Refused",
      badge("b-red", "Can’t undo safely", "warn") +
        badge("b-red", "Checker refused", "warn") +
        badge("b-red", "Guidance has 2 problems", "warn"),
    ],
    [
      "Neutral",
      badge("b-nt", "Not saved") +
        badge("b-nt", "Not moved") +
        badge("b-nt", "No type") +
        badge("b-nt", "No guidance yet") +
        badge("b-nt", "Nothing yet") +
        badge("b-nt", "Undo requested") +
        badge("b-nt", "Replaced"),
    ],
  ];
  const sentences = [
    ["Frozen after approve", "“You approved this.”"],
    ["Frozen after Not now", "“Not saved.” · “Not moved.”"],
    ["Frozen after Undo", "“You asked to undo this.”"],
    [
      "Why it waits",
      "“Waits for you because it changes &lt;file&gt;. Every saved edit is recorded and can be undone.”",
    ],
    ["Left out", "“&lt;n&gt; files left out: &lt;names&gt;.” then “Show why”"],
    [
      "Composer hint while waiting",
      "“Allow above, or say what to change instead” (host composer, our words)",
    ],
  ];
  const buttons = [
    [
      "Primary: verb + exactly what",
      "“Save C1–C4” · “Save C2–C4” · “Move 3 files” · “Create the file” · “Apply 2 changes”",
    ],
    ["Secondary", "“Not now” · “Undo” · “Prepare again”"],
    [
      "Disclosure (in the body, not an action)",
      "“Show why” · “Show the 5 links” · “Show the change”",
    ],
    [
      "Never",
      "“OK”, “Submit”, “Confirm”, “Yes” alone on a card that writes; “Add a note” or any text field (text goes in chat)",
    ],
  ];

  const F = [
    {
      id: "F00",
      name: "Claude MCP Apps requirements",
      layer: "Checklist",
      h: 1500,
      purpose:
        "Every rule Claude’s documentation and the MCP Apps spec set for this card, checked against the storyboard. Read before building; re-check after any change. Sources were read on 2026-10-28.",
      body: `<div class="one">${tbl(
        ["Requirement", "Source", "Status", "Where"],
        [
          [
            "Transparent html and body; color-scheme “light dark”",
            "mcp-apps/transparent-theming",
            badge("b-grn", "Met", "check"),
            "kmgen; P01",
          ],
          [
            "Host style variables for all structure; no hardcoded colours",
            "mcp-apps/design-guidelines",
            badge("b-grn", "Met", "check"),
            "F01 (fallbacks = Claude’s values)",
          ],
          [
            "Three sizes, two weights",
            "mcp-apps/design-guidelines",
            badge("b-grn", "Met", "check"),
            "F02",
          ],
          [
            "Host radius and 0.5px border; no shadows needed",
            "mcp-apps/design-guidelines",
            badge("b-grn", "Met", "check"),
            "F03",
          ],
          [
            "Light and dark, tested",
            "mcp-apps/design-guidelines",
            badge("b-grn", "Met", "check"),
            "Every frame in both",
          ],
          [
            "At most 2 actions, at the bottom",
            "mcp-apps/design-guidelines",
            badge("b-grn", "Met", "check"),
            "All 36 states checked by script",
          ],
          [
            "At most 4–5 data points per inline card",
            "mcp-apps/design-guidelines",
            badge("b-grn", "Met", "check"),
            "Recommendation 1 amended: summary inline, full table in the full view (9 full views). The generator refuses an inline card over 5 data points.",
          ],
          [
            "Height fits content; no nested scrolling; mobile clips tall cards",
            "mcp-apps/design-guidelines",
            badge("b-grn", "Met", "check"),
            "Inline cards are summaries; long tables live in the full view",
          ],
          [
            "Full screen: the app provides its own fullscreen button; composer always visible; no floating panels",
            "mcp-apps/design-guidelines",
            badge("b-grn", "Met", "check"),
            "K13 Full view button; P07; tabs in M02",
          ],
          [
            "No menus, popovers, drill-ins or multiple views",
            "mcp-apps/design-guidelines",
            badge("b-grn", "Met", "check"),
            "K11 segmented choice; disclosures stay in place",
          ],
          [
            "Text entry, refining and follow-ups go in chat",
            "mcp-apps/design-guidelines",
            badge("b-grn", "Met", "check"),
            "Note field removed; E04, C02, M05 use chat",
          ],
          [
            "Skeletons, not spinners, while loading inline",
            "mcp-apps/design-guidelines",
            badge("b-grn", "Met", "check"),
            "K10; O01",
          ],
          [
            "Tap targets at least 44 × 44pt",
            "mcp-apps/design-guidelines",
            badge("b-grn", "Met", "check"),
            "K02, K05, K11 rules; verify in build",
          ],
          [
            "320px up, container queries, safe areas, nothing flush to an edge",
            "mcp-apps/design-guidelines",
            badge("b-amb", "Gap"),
            "Rules in F03 and F06; only P02 is drawn narrow. Every card needs a 320px frame.",
          ],
          [
            "WCAG AA, keyboard navigation, text alternatives",
            "mcp-apps/design-guidelines",
            badge("b-amb", "Partly"),
            "Contrast computed in F01; focus states in K02, K05; keyboard order and screen-reader labels not specified yet",
          ],
          [
            "Older cards disable themselves (no host unmount)",
            "mcp-apps/instance-supersession",
            badge("b-amb", "Gap"),
            "Designed in P06 and E04; needs a server key in each result’s structuredContent (contract change)",
          ],
          [
            "Meaningful text content for hosts without Apps",
            "ext-apps spec (MUST)",
            badge("b-amb", "Gap"),
            "Only kb_prepare_proposal, kb_record_edit and kb_list_edits have text cards; see each flow’s “Every surface” frame",
          ],
          [
            "Claude Code shows no card; the model gets structuredContent as a JSON string",
            "mcp-apps/quickstart",
            badge("b-grn", "Met", "check"),
            "card field inside structuredContent (0.4.0)",
          ],
          [
            "ui:// resource, MIME text/html;profile=mcp-app, valid HTML5; declared in tool _meta.ui.resourceUri",
            "ext-apps spec (MUST)",
            badge("b-nt", "At build"),
            "mcp.server.apps in mcp 2.2.0",
          ],
          [
            "CSP: nothing external undeclared; host fonts from https://assets.claude.ai in resourceDomains; no frameDomains in Claude",
            "ext-apps spec; mcp-apps/transparent-theming",
            badge("b-nt", "At build"),
            "No external assets in the design",
          ],
          [
            "Buttons send ui/message; the host may ask consent; Claude asks “Allow / Always allow” before first display",
            "ext-apps spec; mcp-apps/getting-started",
            badge("b-grn", "Met", "check"),
            "P06; K12 (host-owned)",
          ],
          [
            "Tool title and readOnlyHint or destructiveHint on every tool (directory listing)",
            "connectors/building/submission",
            badge("b-grn", "Met", "check"),
            "All 20 tools in tools.json have a title and annotations",
          ],
          [
            "Tool call under 240 s; result under about 150,000 characters",
            "connectors/building; mcp-apps/troubleshooting",
            badge("b-nt", "At build"),
            "Large move plans need a check",
          ],
        ],
      )}</div>`,
      tokens: [],
      rules: [
        "A requirement marked Met stays met: re-run the action-count check after any flow change.",
        "Your ruling items block the cards they name, not the rest.",
      ],
    },
    {
      id: "F01",
      name: "Colour",
      layer: "Foundation",
      h: 1100,
      purpose:
        "Every colour is a Claude host style variable. Values here are Claude’s documented ones, used only as fallbacks outside a host. The card paints no background: Claude’s chat shows through.",
      body: `<div class="one">${tbl(["Token", "Light fallback", "Dark fallback", "Use"], colourRows)}</div><div class="one">${tbl(["Status pair", "Light", "Dark", "Contrast L · D", "Means"], statusRows)}</div><div class="one">${tbl(["Text check (AA 4.5:1)", "Light", "Dark"], textChecks)}</div>`,
      tokens: ["--color-*"],
      rules: [
        "Three status meanings: waiting, done, refused. Anything else is neutral.",
        "Never hardcode a colour; brand colour only as an accent (Claude).",
        "Waiting is the only colour that pulses.",
        "No colour carries meaning alone: every badge has words.",
      ],
    },
    {
      id: "F02",
      name: "Typography",
      layer: "Foundation",
      h: 760,
      purpose:
        "Claude’s rule: three sizes (heading, body, caption) and two weights (regular, emphasized). The host supplies the font (Anthropic Sans in Claude) at runtime.",
      body: two(
        tbl(["Token", "Sample", "Use"], typeRows) +
          `<div class="one">${vr([
            ["--font-sans", `<span>${T.font["--font-sans"]}</span>`],
            [
              "--font-mono",
              `<span class="mono">${T.font["--font-mono"]}</span>`,
            ],
            [
              "Weights",
              "<span>400 regular · 600 emphasized. Nothing else.</span>",
            ],
          ])}</div>`,
      ),
      tokens: [
        "--font-sans",
        "--font-mono",
        "--font-weight-normal|semibold",
        "--font-heading-md-*",
        "--font-text-sm-*",
        "--font-text-xs-*",
      ],
      rules: [
        "No size outside these three.",
        "Mono only for paths, places, tool names and C-numbers, at body or caption size.",
        "Fonts come from the host (styles.css.fonts, applyHostFonts); bundle any font of our own, never a public CDN.",
      ],
    },
    {
      id: "F03",
      name: "Space, radius, border, elevation",
      layer: "Foundation",
      h: 900,
      purpose:
        "Spacing has no host variable, so it is ours (--km-space-*). Radius and border width come from the host: in Claude a border is 0.5px. No shadows.",
      body: `<div class="one">${tbl(
        ["Token", "Size", "", "Use"],
        Object.entries(T.space).map(([k, v]) => [
          `<span class="mono">${k}</span>`,
          v,
          `<div class="bar" style="width:${parseInt(v) * 4}px"></div>`,
          T.spaceUse[k],
        ]),
      )}</div><div class="one">${tbl(
        ["Token", "Size", "", "Use"],
        Object.entries(T.radius).map(([k, v]) => [
          `<span class="mono">${k}</span>`,
          v,
          `<div class="rbox" style="border-radius:${v === "9999px" ? "22px" : v}"></div>`,
          T.radiusUse[k],
        ]),
      )}</div><div class="one">${vr([
        [
          "Border",
          '<span class="mono">--border-width-regular</span> 0.5px in Claude, colour <span class="mono">--color-border-tertiary</span> for dividers',
        ],
        [
          "Card frame",
          'Not ours. We set <span class="mono">_meta.ui.prefersBorder: true</span>, so Claude draws the border and padding on web and mobile alike (unset, it is borderless on web, bordered on mobile).',
        ],
        [
          "Elevation",
          'None. Claude offers <span class="mono">--shadow-*</span>; a card sits in the chat, not above it.',
        ],
      ])}</div>`,
      tokens: ["--km-space-1…6", "--border-radius-*", "--border-width-regular"],
      rules: [
        "Nothing interactive flush against an edge: keep --km-space-6 clear (Claude: the composer can overlay the bottom).",
        "No margin values outside the scale.",
        "No shadows, no gradients.",
      ],
    },
    {
      id: "F04",
      name: "Icons",
      layer: "Foundation",
      h: 760,
      purpose:
        "18 line icons on a 16px grid, 1.4px stroke, drawn at 13px in text and 18px here. They take the text colour around them.",
      body:
        two(
          `<div class="icg">${icons.map(([n, u]) => `<div>${ic[n]}<b class="mono" style="color:var(--color-text-primary)">${n}</b><span style="text-align:center">${u}</span></div>`).join("")}</div>`,
        ) +
        `<div class="one">${tbl(
          [
            "Evidence mark",
            "In the app",
            "In the text card (hosts without Apps)",
          ],
          [
            ["Supported", evTag("supported"), "● Supported"],
            ["Partly answered", evTag("partly"), "◐ Partly answered"],
            ["Conflicting", evTag("conflicting"), "✕ Conflicting"],
            ["Suggested", evTag("suggested"), "◆ Suggested"],
          ],
        )}</div>`,
      tokens: ["currentColor", "13px in text"],
      rules: [
        "An icon never stands alone without a label, except Undo’s arrow inside a labelled button.",
        "Text-card glyphs come from views/markdown.py MARKS; the words must match exactly.",
      ],
    },
    {
      id: "F05",
      name: "Motion",
      layer: "Foundation",
      h: 560,
      purpose:
        "Two motions only. The pulse means “waiting on you”. The skeleton shimmer means “loading”. Claude: “Avoid spinners for inline content.”",
      body: two(
        vr([
          [
            "Pulse · --km-pulse",
            badge("b-amb", "Needs your OK") +
              '<span class="mu">1.6s ease-out, repeats</span>',
          ],
          [
            "Skeleton · --km-shimmer",
            '<span style="width:220px"><span class="sk t"></span><span class="sk"></span><span class="sk s"></span></span>',
          ],
          [
            "Reduced motion",
            '<span class="badge b-amb"><i class="pulse" style="animation:none"></i>Needs your OK</span><span class="mu">dot stays, no ring; skeleton holds still</span>',
          ],
          [
            "Freeze on press",
            '<span class="mu">instant; no fade, no slide</span>',
          ],
        ]),
      ),
      tokens: ["--km-pulse", "--km-shimmer"],
      rules: [
        "No spinner inside a card. Spinners in tool step lines are the host’s.",
        "Never pulse a done, refused or neutral badge.",
        "Respect prefers-reduced-motion.",
      ],
    },
    {
      id: "F06",
      name: "Host, theming and layout",
      layer: "Foundation",
      h: 1100,
      purpose:
        "What Claude gives the card, what the card must do, and what it must never draw. Every row cites the page it comes from; F00 lists them as checks.",
      body: `<div class="one">${tbl(
        ["Concern", "Rule", "Source"],
        [
          [
            "Where it renders",
            "Claude web, Claude Desktop, Claude for iOS and Android, Cowork. Claude Code “calls the tool as text and doesn’t render the UI”. Other hosts: not verified.",
            "support.claude.com 13454812; connectors/building/mcp-apps/quickstart",
          ],
          [
            "Background",
            'Transparent html and body; <span class="mono">&lt;meta name="color-scheme" content="light dark"&gt;</span>; style with host variables, fallbacks for outside a host.',
            "mcp-apps/transparent-theming",
          ],
          [
            "Theme and fonts",
            'Apply <span class="mono">theme</span>, <span class="mono">styles.variables</span>, <span class="mono">styles.css.fonts</span> on connect and on every host-context change. Fonts come from https://assets.claude.ai, so it goes in <span class="mono">csp.resourceDomains</span>.',
            "mcp-apps/transparent-theming",
          ],
          [
            "Display mode",
            "Inline card: at most 2 actions at the bottom, at most 4–5 data points, height fits content, no nested scrolling, no menus, popovers or drill-ins. Full view (fullscreen) for the detail: our own Full view button opens it; Claude draws the header bar, close button and composer; tabs or pagination, never floating panels. Declare inline and fullscreen in availableDisplayModes.",
            "mcp-apps/design-guidelines",
          ],
          [
            "Width and mobile",
            "Fill the container, 320px up, container queries, no fixed breakpoints. Mobile caps inline height and clips. Apply safeAreaInsets; nothing interactive flush against an edge.",
            "mcp-apps/design-guidelines",
          ],
          [
            "Touch",
            "Every tap target at least 44 × 44pt.",
            "mcp-apps/design-guidelines",
          ],
          [
            "Loading",
            "Skeleton in the final layout; no spinner.",
            "mcp-apps/design-guidelines",
          ],
          [
            "App or chat",
            "In the card: selections, toggles, expand/collapse, confirming a prepared action. In chat: any text entry, refining, redoing, follow-ups.",
            "mcp-apps/design-guidelines",
          ],
          [
            "Buttons",
            'A press sends <span class="mono">ui/message</span> (role user); the host may ask your consent. The card never writes.',
            "ext-apps spec; knowledge-mcp opens no files",
          ],
          [
            "Many copies",
            "Every tool call mounts a new card and no host API removes old ones: an older card disables itself when a newer one about the same thing exists (server key in structuredContent).",
            "mcp-apps/instance-supersession",
          ],
          [
            "Sandbox",
            'No external origins unless declared in <span class="mono">_meta.ui.csp</span>; no frames (frameDomains restricted in Claude); no downloads; no camera, microphone or location on mobile.',
            "ext-apps spec; mcp-apps/design-guidelines",
          ],
          [
            "Fallback",
            "Every tool returns meaningful text content too. In Claude Code the model receives structuredContent as a JSON string, card included.",
            "ext-apps spec; mcp-apps/quickstart",
          ],
          [
            "Limits",
            "Tool calls time out at 240 s; results over about 150,000 characters never hydrate the card.",
            "connectors/building; mcp-apps/troubleshooting",
          ],
        ],
      )}</div>`,
      tokens: [
        "theme",
        "styles.variables",
        "styles.css.fonts",
        "safeAreaInsets",
        "containerDimensions",
      ],
      rules: [
        "If it is outside the card, the host draws it.",
        "Design every card at 320px as well as wide.",
      ],
    },
    {
      id: "F07",
      name: "Copy and terms",
      layer: "Foundation",
      h: 1180,
      purpose:
        "The words are part of the system. Labels are fixed strings per state; terms match the user guides; buttons say exactly what they will do.",
      body: `<div class="one">${tbl(
        ["Say", "Not", "Why"],
        terms.map((r) => [
          `<b>${r[0]}</b>`,
          `<span class="mu">${r[1]}</span>`,
          r[2],
        ]),
      )}</div><div class="one">${two(vr(labels))}</div><div class="one">${tbl(["Button", "Exact copy"], buttons)}</div><div class="one">${tbl(["Sentence", "Exact copy"], sentences)}</div>`,
      tokens: ["copy rows"],
      rules: [
        "Sentence case everywhere except the eyebrow.",
        "Summary values: terse noun phrases joined by “ · ”. No articles, no semicolons, no colon inside a value (“slide 7 approved, notes disputed”).",
        "Name the thing: a file, a count, a C-number. Never “this item”.",
        "A refusal always says why and that nothing changed.",
      ],
    },
  ];

  // ---------- Components (elements) ----------
  const st = (label, html) => [label, html];
  const C = [
    {
      id: "K00",
      name: "Layer map",
      layer: "Index",
      h: 900,
      purpose:
        "Where every part lives, by CE layer. Core is vendor and read-only; elements are our vocabulary; patterns compose them; host-owned parts are never built.",
      body: `<div class="one">${tbl(
        ["Layer", "Parts", "Rule"],
        [
          [
            "<b>Core</b>",
            'Button · Badge · Checkbox · Toggle group · Skeleton · Table <span class="mu">(vendor; stack pending your ruling)</span>',
            "Never hand-edited. Wrap in an element to change it.",
          ],
          [
            "<b>Elements</b>",
            "K01 Badge · K02 Button · K03 Evidence mark · K04 Chips · K05 Change number · K06 Note · K07 Text lines · K08 Key–value grid · K09 Diff · K10 Skeleton · K11 Segmented choice · K13 Full view button",
            "0–1 source, at least as many exports as imports.",
          ],
          [
            "<b>Patterns</b>",
            "P01 Card shell · P02 Change table · P03 Left-out disclosure · P04 Decision rows · P05 Result and refusal · P06 Card lifecycle · P07 Summary and full view",
            "2+ sources, fewer exports than imports.",
          ],
          [
            "<b>Host-owned</b>",
            "K12: the card’s border and padding, the full-screen header bar and close button, your messages, sent messages, tool step lines, assistant text, composer, permission prompts",
            "Never built. The storyboard draws them only for context.",
          ],
          [
            "<b>Removed</b>",
            "Note field, “Add a note”, spinner, progress bar",
            "Claude: text entry belongs in chat; no spinners inline.",
          ],
        ],
      )}</div>`,
      tokens: [],
      rules: [
        "Dependencies flow down only: patterns → elements → core.",
        "A part not on this map does not exist yet: raise it before building.",
      ],
      uses: [],
    },
    {
      id: "K01",
      name: "Badge",
      layer: "Element",
      h: 640,
      purpose:
        "The card’s state, top right of the header. One meaning per tone; the copy is fixed per state (F07).",
      body: two(
        vr([
          st(
            "Waiting · pulse",
            badge("b-amb", "Needs your OK") + badge("b-amb", "Nothing saved"),
          ),
          st(
            "Done",
            badge("b-grn", "Saved", "check") +
              badge("b-grn", "Approved", "check"),
          ),
          st("Refused", badge("b-red", "Can’t undo safely", "warn")),
          st("Neutral", badge("b-nt", "Not saved") + badge("b-nt", "No type")),
          st(
            "Reduced motion",
            '<span class="badge b-amb"><i class="pulse" style="animation:none"></i>Needs your OK</span>',
          ),
        ]),
      ),
      tokens: [
        "--color-background-{warning,success,danger,info,secondary}",
        "--color-text-*",
        "--border-radius-full",
        "--font-text-xs-*",
      ],
      rules: [
        "One badge per card.",
        "Only waiting has the dot.",
        "Done carries the check icon; refused the warning icon.",
      ],
      uses: [/class="badge /],
    },
    {
      id: "K02",
      name: "Button",
      layer: "Element",
      h: 700,
      purpose:
        "Three kinds. Primary does the one thing the card is for; secondary and ghost decline or reveal. At most one primary per card.",
      body: two(
        tbl(
          ["", "Default", "Hover", "Focus", "Disabled"],
          [
            [
              "Primary",
              btn("Save C1–C4", "p"),
              btn("Save C1–C4", "p hover"),
              btn("Save C1–C4", "p focus"),
              btn("Move 3 files", "p dis"),
            ],
            [
              "Secondary",
              btn("Undo", "", "undo"),
              btn("Undo", "hover", "undo"),
              btn("Undo", "focus", "undo"),
              btn("Undo", "dis", "undo"),
            ],
            [
              "Ghost",
              btn("Not now", "g"),
              btn("Not now", "g hover"),
              btn("Not now", "g focus"),
              btn("Not now", "g dis"),
            ],
            [
              "With icon",
              btn("Add a note", "g", "note"),
              btn("Show the links", "g", "link"),
              "",
              "",
            ],
          ],
        ),
      ),
      tokens: [
        "--color-background-inverse",
        "--color-text-inverse",
        "--border-radius-md",
        "--color-ring-primary",
      ],
      rules: [
        "At most 2 per card, at the bottom (Claude inline card).",
        "Tap target at least 44pt: min-height under pointer: coarse.",
        "Pressing freezes the card (P06); no loading state on the button.",
        "Disabled says why nearby.",
      ],
      uses: [/class="btn /],
    },
    {
      id: "K03",
      name: "Evidence mark",
      layer: "Element",
      h: 520,
      purpose:
        "How well the sources back a proposed change. Four values from proposal.schema.yaml; the words match the text card.",
      body: two(
        vr([
          st("Supported", evTag("supported")),
          st("Partly answered", evTag("partly")),
          st("Conflicting", evTag("conflicting")),
          st("Suggested (your words)", evTag("suggested")),
        ]),
      ),
      tokens: [
        "--border-radius-full",
        "--color-border-tertiary",
        "--font-text-xs-*",
      ],
      rules: [
        "Above the proposed text, never beside the source.",
        "Neutral tone: a mark describes evidence, it is not a status.",
      ],
      uses: [/class="ev"/],
    },
    {
      id: "K04",
      name: "Chips: source and path",
      layer: "Element",
      h: 620,
      purpose:
        "Exact places the evidence came from, and the file or folder in scope. Mono text, so paths read exactly.",
      body: two(
        vr([
          st("Line source", src("meeting-notes.md:15")),
          st(
            "Place source",
            src("build-timings.xlsx › Evening!A2:D10") +
              src("cache-rollout-review.pptx › slide 7", 1),
          ),
          st("Person source", chip("note", "you: “a proposal … on its own”")),
          st(
            "Same file, another line",
            src("meeting-notes.md:11") +
              '<span class="mu">vs</span>' +
              src(":19"),
          ),
          st(
            "File in scope",
            chip("file", '<span class="mono">cache-proposal.md</span>'),
          ),
          st("Folder in scope", chip("folder", "~/Notes/Build Operations")),
        ]),
      ),
      tokens: ["--border-radius-sm", "--font-mono", "--color-border-tertiary"],
      rules: [
        "One chip per source from the contract: line_source, place_source, person_source.",
        "Never truncate a path in the middle; wrap the row instead.",
      ],
      uses: [/class="chip /],
    },
    {
      id: "K05",
      name: "Change number and tick box",
      layer: "Element",
      h: 520,
      purpose:
        "Names each change C1, C2 … (the contract’s numbering) and lets you keep or leave it out before saving.",
      body: two(
        vr([
          st(
            "Kept",
            `<span class="cn"><span class="cb">${ic.check}</span>C1</span>`,
          ),
          st(
            "Left out",
            '<span class="cn"><span class="cb off"></span>C1</span>',
          ),
          st(
            "Focus",
            `<span class="cn"><span class="cb" style="box-shadow:var(--km-focus-ring)">${ic.check}</span>C1</span>`,
          ),
          st("Frozen card (no box)", '<span class="cn">C1</span>'),
          st(
            "Header · all selected",
            `<span class="cn"><span class="cb">${ic.check}</span>All</span>`,
          ),
          st(
            "Header · some left out",
            '<span class="cn"><span class="cb mixed"></span>All</span>',
          ),
        ]),
      ),
      tokens: [
        "--border-radius-xs",
        "--font-mono",
        "--color-background-inverse",
      ],
      rules: [
        "The number never changes within a card, even when a row is left out.",
        "The whole row is the tap target (44pt), not the 15px box.",
        "Typing “drop C1” in chat is the same as unticking.",
      ],
      uses: [/class="cn"/],
    },
    {
      id: "K06",
      name: "Note",
      layer: "Element",
      h: 600,
      purpose:
        "A quiet block inside a card for something you should know before deciding. Three kinds, one icon each.",
      body: two(
        `<div class="note">${ic.info}<span><b>No naming rule for Design proposals</b> (dropped in conventions), so it goes beside cache-proposal.md.</span></div><div class="note">${ic.left}<span><b>2 files left out:</b> vendor-quote.xlsx, release-calendar.md. <u>Show why</u></span></div><div class="note">${ic.warn}<span>Prepared again because the file changed. C2’s current text is new.</span></div>`,
      ),
      tokens: [
        "--color-background-secondary",
        "--border-radius-lg",
        "--km-space-4/5",
      ],
      rules: [
        "Bold the fact, then the reason.",
        "A warning note never replaces the refused badge; it explains it.",
      ],
      uses: [/class="note"/],
    },
    {
      id: "K07",
      name: "Text lines",
      layer: "Element",
      h: 620,
      purpose:
        "The fixed text roles inside a card. Each has one style; nothing else is styled ad hoc.",
      body: two(
        vr([
          st("Eyebrow", '<span class="eb">Proposed changes</span>'),
          st(
            "Title",
            '<span class="tt">Focus the proposal on retiring the evening build</span>',
          ),
          st(
            "Meta",
            '<span class="meta">Design proposal · for maintainers deciding whether to accept it</span>',
          ),
          st(
            "Why line",
            '<span class="why" style="margin:0">Waits for you because it changes cache-proposal.md.</span>',
          ),
          st(
            "Frozen line",
            '<span class="frozen" style="margin:0">You approved this.</span>',
          ),
          st(
            "Current text",
            '<span><span class="k">Title:</span> <span class="mu">Build schedule and cache rollout</span></span>',
          ),
        ]),
      ),
      tokens: [
        "--font-text-xs/sm/md",
        "--font-heading-xs",
        "--color-text-tertiary",
      ],
      rules: [
        "Eyebrow names the card kind; title names this instance.",
        "Copy for why and frozen lines is fixed (F07).",
      ],
      uses: [/class="eb"/, /class="why"/, /class="frozen"/],
    },
    {
      id: "K08",
      name: "Key–value grid",
      layer: "Element",
      h: 520,
      purpose:
        "The inline summary’s data points, label left, value right. At most five rows: the generator refuses more.",
      body: two(
        `<div class="grid2"><div class="mu">Reader</div><div>Maintainers deciding whether to accept it</div><div class="mu">Guidance</div><div>product-dev · Design proposal</div><div class="mu">Since then</div><div><b>4 new files, 1 moved</b> · 3 can be filed by your conventions</div></div>`,
      ),
      tokens: ["--km-space-3/5", "--color-text-tertiary"],
      rules: ["Labels are nouns from F07 terms.", "Narrow: label above value."],
      uses: [/class="grid2"/],
    },
    {
      id: "K09",
      name: "Diff",
      layer: "Element",
      h: 480,
      purpose:
        "The exact before and after of a saved edit, from the edit record.",
      body: two(
        '<div class="diff"><div class="dm">Title: Build schedule and cache rollout</div><div class="dp">Title: Evening build retirement</div></div>',
      ),
      tokens: [
        "--color-background-danger/success",
        "--color-text-danger/success",
      ],
      rules: [
        "Only on result cards, behind “Show the change”.",
        "Removed lines struck through, so the meaning survives without colour.",
      ],
      uses: [/class="diff"/],
    },
    {
      id: "K10",
      name: "Skeleton",
      layer: "Element",
      h: 520,
      purpose:
        "Loading, in the shape of the card that will replace it. Claude: “Show skeleton screens … Avoid spinners for inline content.”",
      body: two(
        `<div style="width:100%"><span class="sk s"></span><span class="sk t"></span><span class="sk row"></span><span class="sk row"></span><span class="sk row"></span></div>`,
      ),
      tokens: [
        "--color-background-secondary",
        "--border-radius-lg",
        "--km-shimmer",
      ],
      rules: [
        "Match the final layout: header, rows, actions.",
        "Only while the card waits for its own tool result; work across calls shows in the host’s step lines.",
      ],
      uses: [/class="sk/],
    },
    {
      id: "K11",
      name: "Segmented choice",
      layer: "Element",
      h: 520,
      purpose:
        "A visible choice among two or three options, for one row or one question. Claude prefers visible controls to menus and dropdowns.",
      body: two(
        vr([
          st(
            "Undecided",
            '<span class="seg"><span>Accept</span><span>Drop</span></span>',
          ),
          st(
            "Accepted",
            '<span class="seg"><span class="on">Accept</span><span>Drop</span></span>',
          ),
          st(
            "Three options",
            '<span class="seg"><span class="on">Decision record</span><span>Meeting notes</span><span>Neither</span></span>',
          ),
        ]),
      ),
      tokens: [
        "--border-radius-sm",
        "--color-border-secondary",
        "--color-background-inverse",
      ],
      rules: [
        "A selection, not an action: it never sends anything by itself.",
        "Each segment is a 44pt tap target on touch.",
        "Anything needing words (a new name, a new folder) goes in chat.",
      ],
      uses: [/class="seg"/],
    },
    {
      id: "K12",
      name: "Host-owned: never build",
      layer: "Host",
      h: 760,
      purpose:
        "Drawn by Claude, not by us: the card’s border and padding (prefersBorder), messages, step lines, the composer, and the prompts Claude shows: “Allow / Always allow” before a card first displays, consent before a sent message, and the “Open external link” modal.",
      body: two(
        `<div class="host-o"><span class="lbl">your message</span>${K.user("Bring the meeting notes into the cache proposal", "Build Operations")}</div><br><div class="host-o"><span class="lbl">sent from the card (ui/message, role user)</span>${K.sent("Save C1–C4 to cache-proposal.md")}<div class="mu" style="font-size:12px">The host shows this as your own message. The dashed outline is a storyboard marker only.</div></div><br><div class="host-o"><span class="lbl">tool step lines</span>${K.tool("kb_prepare_proposal", "C1–C4 · 2 files left out")}${K.tool("kb_record_edit", "recording", 1)}</div><br><div class="host-o"><span class="lbl">composer</span>${K.comp("Build Operations", "Allow above, or say what to change instead")}</div>`,
      ),
      tokens: ["none: host styles"],
      rules: [
        "Never draw a chat bubble, step line, composer or chat input inside a card (Claude: don’t replicate Claude’s own features).",
        "We may suggest the composer hint text; the host decides.",
      ],
      uses: [/class="ubox"/],
    },
    {
      id: "K13",
      name: "Full view button",
      layer: "Element",
      h: 520,
      purpose:
        "Opens the same card in full screen. Claude: “Your app provides its own fullscreen button.” It sits in the header beside the badge, not in the action bar.",
      body: two(
        vr([
          st(
            "Beside the badge",
            `<span class="hr">${badge("b-amb", "Nothing saved")}${K.xbtn}</span>`,
          ),
          st(
            "Focus",
            `<span class="xbtn" style="box-shadow:var(--km-focus-ring)">${ic.expand}Full view</span>`,
          ),
        ]),
      ),
      tokens: [
        "--border-radius-md",
        "--color-border-secondary",
        "--font-text-xs-*",
      ],
      rules: [
        "Only on a card whose summary hides detail.",
        "Not an action: it does not count toward the two.",
        "Requests fullscreen with ui/request-display-mode; only if the host lists fullscreen in availableDisplayModes.",
      ],
      uses: [/class="xbtn"/],
    },
  ];

  // ---------- Patterns ----------
  const head = {
    eb: "Proposed changes",
    title: "Focus the proposal on retiring the evening build",
    meta: `${chip("file", '<span class="mono">cache-proposal.md</span>')} Design proposal · for maintainers deciding whether to accept it`,
  };
  const rowsLive = (n) =>
    `<table class="rows ${n ? "narrow" : ""}"><tr><th style="width:50px"></th><th>Current</th><th>Proposed</th><th>Source</th></tr><tr><td><span class="cn"><span class="cb">${ic.check}</span>C1</span></td><td><span class="k">Title:</span> <span class="mu">Build schedule and cache rollout</span></td><td>${evTag("suggested")}<span class="k">Title:</span> Evening build retirement</td><td class="srcs">${src("meeting-notes.md:15")}</td></tr><tr class="out"><td><span class="cn"><span class="cb off"></span>C2</span></td><td><span class="k">Motivation:</span> <span class="mu">evening build never finishes</span></td><td>${evTag("supported")}<span class="k">Motivation:</span> 7 of 9 evening runs hit the 6-hour limit</td><td class="srcs">${src("build-timings.xlsx › Evening!A2:D10")}</td></tr></table>`;
  const anat = `<div class="km"><div class="kmh"><div><div class="eb"><span class="ann">1</span>Proposed changes</div><div class="tt"><span class="ann">2</span>Focus the proposal on retiring the evening build</div><div class="meta"><span class="ann">3</span>${head.meta}</div></div><span><span class="ann">4</span>${badge("b-amb", "Nothing saved")}</span></div><div style="display:flex;align-items:flex-start"><span class="ann" style="margin-top:14px">5</span><div style="flex:1">${rowsLive(0)}</div></div><div class="why"><span class="ann">6</span>Waits for you because it changes cache-proposal.md.</div><div class="acts"><span class="ann">7</span>${btn("Save C1", "p")}${btn("Not now", "g")}</div></div>`;
  const legend = `<ul class="legend">${["Eyebrow: the card kind (K07)", "Title: this instance (K07)", "Meta: scope chip and context (K04, K07)", "Badge: one state (K01)", "Body: a pattern or element per card kind", "Why line: why it waits (K07)", "Action bar: at most 2, primary then decline (K02)"].map((t, i) => `<li><span class="ann">${i + 1}</span>${t}</li>`).join("")}</ul>`;
  const pick = (on) =>
    `<span class="seg"><span class="${on === "a" ? "on" : ""}">Accept</span><span class="${on === "d" ? "on" : ""}">Drop</span></span>`;
  const decision = (state) =>
    tbl(
      ["Document type", "Folder", "Example", ""],
      [
        [
          "Decision record",
          "Decisions/",
          '<span class="mono">Decisions/2026-10-28 retire evening build.md</span>',
          state === 0 ? pick("") : badge("b-grn", "Accepted", "check"),
        ],
        [
          "Meeting notes",
          "Calendar/Meetings/",
          '<span class="mono">Calendar/Meetings/2026-10-27 build review.md</span>',
          state === 0 ? pick("a") : badge("b-grn", "Accepted", "check"),
        ],
        [
          "Design proposal",
          "Proposals/",
          '<span class="mono">Proposals/timings-notes.md</span>',
          state === 0 ? pick("d") : badge("b-nt", "Dropped"),
        ],
      ],
      "rows",
    );
  const P = [
    {
      id: "P01",
      name: "Card shell",
      layer: "Pattern",
      h: 1000,
      purpose:
        "Every card has the same frame: header, body, why line, action bar. Kinds differ only in the body.",
      body:
        `<div class="one" style="display:grid;grid-template-columns:1.6fr 1fr;gap:28px;align-items:start"><div>${anat}</div><div>${legend}</div></div>` +
        two(
          card({
            ...head,
            badge: badge("b-amb", "Nothing saved"),
            acts: `${btn("Save C1–C4", "p")}${btn("Not now", "g")}`,
          }) +
            card({
              ...head,
              eb: "Change",
              badge: badge("b-grn", "Approved", "check"),
              body: '<div class="frozen">You approved this.</div>',
            }),
        ),
      tokens: ["--border-radius-xl", "--km-space-6", "--color-border-tertiary"],
      rules: [
        "No background of its own: transparent, so Claude’s chat shows through; Claude draws the border (prefersBorder: true).",
        "Header order is fixed: eyebrow, title, meta; badge right.",
        "Frozen: actions removed, frozen line added, body unchanged.",
      ],
      uses: [/class="km"/],
    },
    {
      id: "P02",
      name: "Change table",
      layer: "Pattern",
      h: 1040,
      purpose:
        "Proposed changes, one row per Cn: what is there now, what is proposed with its evidence mark, and the exact sources.",
      body: two(
        `<div class="km" style="margin:0">${rowsLive(0)}</div><div class="mu" style="margin:14px 0 8px;font-size:12px">Narrow (under 560px): each row stacks</div><div class="km narrowbox" style="margin:0">${rowsLive(1)}</div>`,
      ),
      tokens: ["K03, K04, K05, K07"],
      rules: [
        "Additions show “— addition” as current text.",
        "A left-out row is struck through and dimmed, never removed.",
        "The header box selects or clears every row; it shows a dash when some rows are left out.",
        "Frozen tables drop the tick boxes but keep the numbers.",
      ],
      uses: [/class="cn"><span class="cb/],
    },
    {
      id: "P03",
      name: "Left-out disclosure",
      layer: "Pattern",
      h: 560,
      purpose:
        "Files read but not cited, always present, closed by default, each with its reason when opened (Strategic Theme 2).",
      body: two(
        `<div class="note">${ic.left}<span><b>2 files left out:</b> vendor-quote.xlsx, release-calendar.md. <u>Show why</u></span></div><div class="note lo-n">${ic.left}<div><b>2 files left out</b><ul class="lo"><li>${src("vendor-quote.xlsx")}<span>Prices a hosted build service. This proposal decides on retiring a build, so it answers none of its questions.</span></li><li>${src("release-calendar.md")}<span>Covers release dates, which this proposal doesn’t.</span></li></ul></div></div>`,
      ),
      tokens: ["K06, K04"],
      rules: [
        "Never hide the count, even at zero (“Nothing left out”).",
        "Reasons come from left_out; the card never invents one.",
      ],
      uses: [/<b>\d+ files? left out/],
    },
    {
      id: "P04",
      name: "Decision rows",
      layer: "Pattern",
      h: 760,
      purpose:
        "When each row needs its own answer: conventions, guidance changes, move blockers. The card’s primary action waits until rows are answered.",
      body: two(
        `<div class="km" style="margin:0">${decision(0)}</div><div class="km">${decision(1)}</div>`,
      ),
      tokens: ["K01, K02, K04"],
      rules: [
        "Each row: a segmented choice (K11), not buttons. Changing a row’s value happens in chat.",
        "Decided rows show a badge in place of the choice.",
        "The primary button counts what will be saved.",
      ],
      uses: [/class="seg"/],
    },
    {
      id: "P05",
      name: "Result and refusal",
      layer: "Pattern",
      h: 720,
      purpose:
        "Every outcome is a new card. A result says what was saved, when and on whose OK, with Undo. A refusal says why and that nothing changed.",
      body: two(
        card({
          eb: "Saved",
          title: "cache-proposal.md · 4 changes",
          meta: "Recorded Oct 28, 09:41 · approved by you",
          badge: badge("b-grn", "Saved", "check"),
          acts: `${btn("Undo", "", "undo")}${btn("Show the change", "g")}`,
        }) +
          card({
            eb: "Undo",
            title: "Undo: cache-proposal.md · 4 changes",
            badge: badge("b-red", "Can’t undo safely", "warn"),
            body: `<div class="note">${ic.warn}<span>cache-proposal.md changed after this edit (2 later edits). Nothing was changed.</span></div>`,
            acts: btn("Show the later edits", "p"),
          }),
      ),
      tokens: ["K01, K02, K06, K07"],
      rules: [
        "Undo is on every result card and is itself a recorded change.",
        "A refusal offers the next useful step, never a retry of the same thing.",
      ],
      uses: [/'Undo'|>Undo</, /b-red/],
    },
    {
      id: "P06",
      name: "Card lifecycle",
      layer: "Pattern",
      h: 760,
      purpose: "The behaviour every card shares. Builders implement this once.",
      body: `<div class="one flow"><div class="st"><b>1 · Drawn live</b>A tool result draws the card: waiting badge, actions on.</div><span class="arr">→</span><div class="st"><b>2 · You press</b>The card freezes at once and sends a ui/message naming exactly what (C-numbers, counts, note).</div><span class="arr">→</span><div class="st"><b>3 · The assistant acts</b>It rereads the files, checks they still hold the previewed text, writes, records.</div><span class="arr">→</span><div class="st"><b>4 · A new card</b>Result, refusal, or the proposal prepared again. The old card never changes.</div><span class="arr">→</span><div class="st"><b>5 · Older cards stand down</b>A live card that sees a newer card about the same file greys out as Replaced (server key, BroadcastChannel).</div></div><div class="one">${tbl(
        ["Rule", "Why"],
        [
          [
            "A card never changes after it is drawn, except to freeze on press.",
            "The app sees only its own tool result; it cannot know what happened next.",
          ],
          [
            "A button never writes.",
            "knowledge-mcp opens no knowledge-base file; the assistant writes.",
          ],
          [
            "Typing in chat works the same as pressing.",
            "“Save C2–C4” in the composer equals the button.",
          ],
          [
            "A card cannot remember a press after a reload.",
            "Claude remounts cards from the transcript; a newer card about the same file marks the old one Replaced instead.",
          ],
          [
            "Progress belongs to one call; across calls the host’s step lines show it.",
            "Recommendation 6.",
          ],
          [
            "Every write waits for an OK and is recorded; every result offers Undo.",
            "S2; recommendation 4.",
          ],
        ],
      )}</div>`,
      tokens: [],
      rules: [
        "Frozen states: Approved · Not saved · Not moved · Undo requested.",
        "No optimistic “Saved” on press: saved is only what a result card says.",
      ],
      uses: [/class="ubub sent"/],
    },
    {
      id: "P07",
      name: "Summary and full view",
      layer: "Pattern",
      h: 900,
      purpose:
        "Amended recommendation 1. A dense card shows a summary inline: at most five data points and two actions. Full view opens the same card in full screen with the whole table and per-row choices.",
      body:
        `<div class="one flow"><div class="st"><b>Inline summary</b>Header with the Full view button · up to 5 data points, the riskiest first (a conflict, a blocker) · why it waits · 2 actions.</div><span class="arr">→</span><div class="st"><b>Full view</b>Same card instance, flat inside Claude’s full-screen chrome · the full table, tick boxes, segmented choices, left-out reasons · tabs for a second table · the same 2 actions above the composer.</div><span class="arr">→</span><div class="st"><b>Press in either</b>The card freezes and sends one message; in the full view it also asks to return inline. Choices made in the full view show in the summary’s button (“Save C2–C4”).</div></div>` +
        two(
          card({
            eb: "Proposed changes",
            title: "Focus the proposal on retiring the evening build",
            badge: badge("b-amb", "Nothing saved"),
            full: true,
            body: K.sum([
              ["Changes", "C1–C4: title, motivation, status, open question"],
              [
                "Evidence",
                "1 supported · 1 partly answered · 1 conflicting · 1 suggested",
              ],
              ["Needs you", "<b>C3 conflicts</b>"],
              ["Left out", "2 files"],
            ]),
            acts: `${btn("Save C1–C4", "p")}${btn("Not now", "g")}`,
          }),
        ),
      tokens: ["K08, K13, P01, P02"],
      rules: [
        "Lead with what needs the person: a conflict, a blocker, a guess.",
        "Never approve something the summary hides without saying it exists: counts and the riskiest item are always inline.",
        "Selections and tabs live in the full view; text still goes in chat.",
      ],
      uses: [/class="xbtn"|class="km flat/],
    },
  ];

  // "Used in": computed from the flow specs, so it cannot drift from the storyboard.
  const flows = () => {
    const all = [...window.FLOW03];
    for (const F of Object.values(window.FLOWS_REST)) all.push(...F);
    return all;
  };
  const usedIn = (sheet) =>
    !sheet.uses
      ? null
      : flows()
          .filter((s) => sheet.uses.some((re) => re.test(s.content)))
          .map((s) => s.id);
  const html = (theme, s) => {
    const ids = usedIn(s);
    return `<!doctype html><html><head><meta charset="utf-8"><style>${K.css}${css}</style></head><body class="${theme}"><div class="sheet"><div class="sh"><div><div class="sid">${s.id}</div><div class="sn">${s.name}</div><div class="sp2">${s.purpose}</div></div><span class="lay">${s.layer}</span></div>${s.body}<div class="foot"><div><h4>Tokens</h4>${s.tokens.length ? s.tokens.map((t) => `<div class="mono">${t}</div>`).join("") : '<span class="mu">—</span>'}</div><div><h4>Rules</h4><ul>${s.rules.map((r) => `<li>${r}</li>`).join("")}</ul></div><div><h4>Used in</h4>${ids === null ? '<span class="mu">Every frame</span>' : ids.length ? `<div class="ids">${ids.map((i) => `<span>${i}</span>`).join("")}</div>` : '<span class="mu">—</span>'}</div></div></div></body></html>`;
  };
  return {
    pages: { "p00-foundations": F, "p00-components": C, "p00-patterns": P },
    html,
  };
})();
("ok");
