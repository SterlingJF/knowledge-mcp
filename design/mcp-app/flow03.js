(() => {
  const K = window.KM,
    { ic, chip, src, evTag, badge, btn, user, sent, tool, comp, card, sum } = K;
  const ask = user(
    "Bring the meeting notes into the cache proposal",
    "Build Operations",
  );
  const trace = tool(
    "kb_get_document_type",
    "Design proposal · read by maintainers deciding whether to accept it",
  );
  const imports = tool(
    "kb_prepare_import",
    "5 sources split into passages, one call each",
  );
  const proposal = tool("kb_prepare_proposal", "C1–C4 · 2 files left out");
  const head = {
    eb: "Proposed changes",
    title: "Focus the proposal on retiring the evening build",
    meta: `${chip("file", '<span class="mono">cache-proposal.md</span>')} Design proposal · for maintainers deciding whether to accept it`,
  };
  const R = [
    [
      `<span class="k">Title:</span> <span class="mu">Build schedule and cache rollout</span>`,
      `${evTag("suggested")}<span class="k">Title:</span> Evening build retirement`,
      `${src("meeting-notes.md:15")}`,
    ],
    [
      `<span class="k">Motivation:</span> <span class="mu">evening build never finishes</span>`,
      `${evTag("supported")}<span class="k">Motivation:</span> 7 of 9 evening runs hit the 6-hour limit`,
      `${src("build-timings.xlsx › Evening!A2:D10")}`,
    ],
    [
      `<span class="mu">— addition</span>`,
      `${evTag("conflicting")}<span class="k">Status:</span> Proposed. Approval is disputed.`,
      `${src("cache-rollout-review.pptx › slide 7", 1)}${src("meeting-notes.md:11")}<span class="mu">vs</span>${src(":19")}`,
    ],
    [
      `<span class="k">Open question:</span> <span class="mu">what baseline would show build times doubled?</span>`,
      `${evTag("partly")}<span class="k">Still open:</span> no timings from before the cache`,
      `${src("build-timings.xlsx › Evening!A2")}${src("meeting-notes.md:21")}`,
    ],
  ];
  // Full view only: rows carry the contract's Cn numbers; boxes keep or leave out each change.
  const table = (boxes, off = -1, rows = R) =>
    `<table class="rows"><tr><th style="width:${boxes ? 50 : 30}px">${boxes ? `<span class="cn"><span class="cb ${off >= 0 ? "mixed" : ""}">${off >= 0 ? "" : ic.check}</span>All</span>` : ""}</th><th style="width:29%">Current</th><th>Proposed</th><th style="width:29%">Source</th></tr>${rows.map((r, i) => `<tr class="${i === off ? "out" : ""}"><td><span class="cn">${boxes ? `<span class="cb ${i === off ? "off" : ""}">${i === off ? "" : ic.check}</span>` : ""}C${i + 1}</span></td><td>${r[0]}</td><td>${r[1]}</td><td class="srcs">${r[2]}</td></tr>`).join("")}</table>`;
  const live = table(1);
  // Inline: four data points, the most important one being the conflict.
  const summary = (
    changes = "C1 Title · C2 Motivation · C3 Status · C4 Open question",
  ) =>
    sum([
      ["Changes", changes],
      [
        "Evidence",
        "1 supported · 1 partly answered · 1 conflicting · 1 suggested",
      ],
      ["Needs you", "<b>C3 Status</b> · Proposed. Approval is disputed."],
      ["Left out", "vendor-quote.xlsx · release-calendar.md"],
    ]);
  const leftClosed = `<div class="note">${ic.left}<span><b>2 files left out:</b> vendor-quote.xlsx, release-calendar.md. <u>Show why</u></span></div>`;
  const leftOpen = `<div class="note lo-n">${ic.left}<div><b>2 files left out</b><ul class="lo"><li>${src("vendor-quote.xlsx")}<span>Prices a hosted build service. This proposal decides on retiring a build, so it answers none of its questions.</span></li><li>${src("release-calendar.md")}<span>Covers release dates, which this proposal doesn’t.</span></li></ul></div></div>`;
  const why = `<div class="why">Waits for you because it changes cache-proposal.md. Every saved edit is recorded and can be undone.</div>`;
  const acts = (what = "C1–C4") =>
    `${btn(`Save ${what}`, "p")}${btn("Not now", "g")}`;
  const qs = `<div class="say">Two questions before you decide: should the cache rollout get its own proposal, or stay here as background? Is approval Maya's call, as build lead?</div>`;
  const waiting = comp(
    "Build Operations",
    "Allow above, or say what to change instead",
  );
  const idle = comp("Build Operations", "Ask about Build Operations");
  const busy = comp("Build Operations", "Working…", 1);
  const frozen = (b, t) =>
    card({
      ...head,
      eb: "Change",
      badge: b,
      body: summary() + `<div class="frozen">${t}</div>`,
    });
  const F = [
    {
      id: "E01",
      name: "Asked: reading the sources",
      x: 0,
      y: 0,
      content:
        ask +
        trace +
        tool("kb_prepare_import", "meeting-notes.md · 41 passages") +
        tool("kb_prepare_import", "build-timings.xlsx · 3 sheets") +
        tool("kb_prepare_import", "cache-rollout-review.pptx · 12 slides") +
        tool("kb_prepare_import", "vendor-quote.xlsx", 1) +
        busy,
      cap: [
        "Asks the assistant to bring meeting notes into a proposal.",
        "The host’s own step lines: the type, then one import per source, each timing itself. No card yet.",
        "kb_get_document_type → type, reader; kb_prepare_import splits one source per call. Progress across calls is the host’s, not a card (recommendation 6).",
        "TheDriveAI steps appear and time themselves (pSx_dSHMJl); import.schema.yaml.",
      ],
    },
    {
      id: "E02",
      name: "Review: the summary inline",
      x: 1040,
      y: 0,
      content:
        ask +
        trace +
        imports +
        proposal +
        card({
          ...head,
          badge: badge("b-amb", "Nothing saved"),
          full: true,
          body: summary() + why,
          acts: acts(),
        }) +
        qs +
        waiting,
      cap: [
        "Reads what would change and decides, or opens the full view to check each change.",
        "Four data points: what changes, how well it is backed, the one conflict, what was left out. Two actions. Full view top right.",
        "kb_prepare_proposal draws the card; nothing saved. Typing “drop C1” works too.",
        "Claude design guidelines: inline at most 4–5 data points, 2 actions; amended recommendation 1.",
      ],
    },
    {
      id: "E02F",
      name: "Full view: every change",
      full: true,
      x: 2080,
      y: 0,
      content: card({
        ...head,
        flat: true,
        badge: badge("b-amb", "Nothing saved"),
        body: live + leftClosed + why,
        acts: acts(),
      }),
      composer: waiting,
      cap: [
        "Pressed Full view.",
        "Every change C1–C4 with its mark, current text and exact sources; a box to keep or leave out each; the files left out.",
        "The same card instance in fullscreen (ui/request-display-mode). Pressing Save here sends the message and returns the card inline.",
        "Claude design guidelines “Reveal complexity progressively”, full screen keeps the composer; proposal.schema.yaml.",
      ],
    },
    {
      id: "E05",
      name: "Approved: the card sends it, the assistant saves",
      x: 0,
      y: 1300,
      content:
        ask +
        proposal +
        frozen(badge("b-grn", "Approved", "check"), "You approved this.") +
        sent("Save C1–C4 to cache-proposal.md") +
        tool("kb_record_edit", "recording the edit to cache-proposal.md", 1) +
        busy,
      cap: [
        "Pressed Save C1–C4, inline or in the full view.",
        "The card freezes inline; its message appears as yours; the save runs.",
        "The button writes nothing: it sends ui/message. The assistant rereads the file, checks each Cn’s current text is still there, writes, then kb_record_edit. Next: Edit result (04).",
        "knowledge-mcp opens no knowledge-base file; MCP Apps ui/message; TheDriveAI approve → frozen card (huFTiG_YBS).",
      ],
    },
    {
      id: "E06",
      name: "If you choose Not now",
      x: 1040,
      y: 1300,
      content:
        frozen(badge("b-nt", "Not saved"), "Not saved.") +
        sent("Not now") +
        `<div class="say">Nothing changed. Tell me what to do differently, for example keep the old title, and I’ll prepare it again.</div>` +
        idle,
      cap: [
        "Presses Not now.",
        'The card freezes as "Not saved."; its message tells the assistant, which asks what to change.',
        "No edit, no record.",
        "TheDriveAI Not now (oC4ZORjRov).",
      ],
    },
    {
      id: "E07",
      name: "If the file changed since the preview",
      x: 2080,
      y: 1300,
      content:
        frozen(badge("b-grn", "Approved", "check"), "You approved this.") +
        sent("Save C1–C4 to cache-proposal.md") +
        tool("kb_prepare_proposal", "prepared again on the current text") +
        `<div class="say">cache-proposal.md changed at 09:45, after this preview: the motivation line C2 replaces is no longer there. Nothing was saved. Here are the changes against the current text.</div>` +
        card({
          ...head,
          badge: badge("b-amb", "Nothing saved"),
          full: true,
          body:
            summary("C1–C4 · C2 current text changed") +
            `<div class="note">${ic.warn}<span>Prepared again because the file changed. Open the full view to see C2’s new current text.</span></div>`,
          acts: acts(),
        }) +
        waiting,
      cap: [
        "Pressed Save after someone else edited the file.",
        "The old card stays frozen. The assistant says nothing was saved and why; a new summary card shows the changes against the current text.",
        "Before writing, the assistant rereads the file; C2’s current text is gone, so it prepares again. Gap: the proposal carries no digest yet (contracts step).",
        "kb-write-document “Recheck … digests”; edit.schema.yaml digests; TheDriveAI “tied to the exact change previewed” (/mcp).",
      ],
    },
    {
      id: "E08",
      name: "Full view: leave a change out",
      full: true,
      x: 0,
      y: 2700,
      content: card({
        ...head,
        flat: true,
        badge: badge("b-amb", "Nothing saved"),
        body: table(1, 0) + leftClosed + why,
        acts: acts("C2–C4"),
      }),
      composer: waiting,
      cap: [
        "Unticks C1 in the full view: keep the old title.",
        "C1 is struck through; the button names what will be saved. Back inline, the summary’s button reads the same.",
        "The message sent is “Save C2–C4 to cache-proposal.md; leave out C1”. Only kept rows are written and recorded.",
        "Per-row selection is in-app direct manipulation (Claude design guidelines); S2 accepted change.",
      ],
    },
    {
      id: "E03",
      name: "Full view: why files were left out",
      full: true,
      x: 1360,
      y: 2700,
      content: card({
        ...head,
        flat: true,
        badge: badge("b-amb", "Nothing saved"),
        body:
          live.replace("<table", '<table style="opacity:.5"') + leftOpen + why,
        acts: acts(),
      }),
      composer: waiting,
      cap: [
        'Opens "Show why" in the full view.',
        "Every file read but not cited, with its reason, in place.",
        "No call: left_out came with the proposal.",
        'proposal.schema.yaml left_out; TheDriveAI "and 2 more" with a reason per item (oC4ZORjRov); Strategic Theme 2.',
      ],
    },
    {
      id: "E04",
      name: "If you say what to change instead",
      x: 2720,
      y: 2700,
      content:
        card({
          ...head,
          eb: "Change",
          badge: badge("b-nt", "Replaced"),
          body:
            summary() + `<div class="frozen">Replaced by the card below.</div>`,
        }) +
        user(
          "Keep the cache rollout as background, and keep the old title",
          "Build Operations",
        ) +
        tool("kb_prepare_proposal", "prepared again: C1–C3") +
        card({
          ...head,
          badge: badge("b-amb", "Nothing saved"),
          full: true,
          body: sum([
            ["Changes", "C1 Motivation · C2 Status · C3 Open question"],
            ["Unchanged", "Title · cache rollout section"],
            ["Needs you", "<b>C2 Status</b> · Proposed. Approval is disputed."],
            ["Left out", "vendor-quote.xlsx · release-calendar.md"],
          ]),
          acts: acts("C1–C3"),
        }) +
        waiting,
      cap: [
        "Types what to change instead of pressing.",
        "The older card greys out as Replaced; a new summary shows the revised changes, numbered afresh.",
        "Text goes through chat, never a field in the card. The older card sees the newer card’s server key and disables itself.",
        "Claude design guidelines “Push these to the chat input”; mcp-apps/instance-supersession.",
      ],
    },
  ];
  window.FLOW03 = F;
})();
("ok");
