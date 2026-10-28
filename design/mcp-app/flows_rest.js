(() => {
  const K = window.KM,
    { ic, chip, src, badge, btn, user, sent, tool, comp, card, sum } = K;
  const cn = (n) => `<span class="cn">C${n}</span>`;
  const S = "Build Operations";
  const idle = comp(S, `Ask about ${S}`),
    wait = comp(S, "Allow above, or say what to change instead"),
    busy = comp(S, "Working…", 1);
  const grid = (rows) =>
    `<div class="grid2">${rows.map(([a, b]) => `<div class="mu">${a}</div><div>${b}</div>`).join("")}</div>`;
  const tbl = (head, rows, style = "") =>
    `<table class="rows" style="${style}"><tr>${head.map((h) => `<th>${h}</th>`).join("")}</tr>${rows.map((r) => `<tr>${r.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</table>`;
  const f = src;
  const dim = (s) =>
    s.replace(
      '<table class="rows" style="',
      '<table class="rows" style="opacity:.5;',
    );
  const P = {};

  // 01 Orientation
  const oAsk = user("What’s this folder about, and where do I start?", S);
  const oGrid = grid([
    [
      "Guidance",
      `2 definition sets: team ${chip("folder", ".knowledge-bus")} and the bundled set`,
    ],
    [
      "Document types",
      'Meeting notes 21 · Decision record 9 · Design proposal 6 · Runbook 4 · <span class="mu">no type 2</span>',
    ],
    ["Conventions", "3 in effect · 1 from the parent folder"],
    ["Last recorded change", "Oct 27, 16:20 · deploy-runbook.md revised"],
    [
      "Since then",
      "<b>4 new files, 1 moved</b> · 3 can be filed by your conventions, 1 has no type",
    ],
  ]);
  P["p01-orientation"] = [
    {
      id: "O01",
      name: "Getting oriented",
      h: 520,
      x: 0,
      y: 0,
      content:
        oAsk +
        tool(
          "kb_prepare_document_types",
          "checking 42 documents and what changed since Oct 26",
          1,
        ) +
        '<div class="km"><span class="sk s"></span><span class="sk t"></span><span class="sk row"></span><span class="sk row"></span><span class="sk row"></span></div>' +
        busy,
      cap: [
        "Opens a session in a folder and asks where to start.",
        "A card that fills in while the folder is read.",
        "kb_prepare_document_types with the file listing; reconciles against the last session (B6).",
        'Docs "Get oriented"; TheDriveAI "What the agent can see" (QOa4K8PSVl).',
      ],
    },
    {
      id: "O02",
      name: "Oriented: what’s here and what changed",
      h: 720,
      x: 1040,
      y: 0,
      content:
        oAsk +
        tool("kb_prepare_document_types", "42 documents · 4 new · 1 moved") +
        tool("kb_list_edits", "last change Oct 27") +
        card({
          eb: "Knowledge base",
          title: S,
          meta: `${chip("folder", "~/Notes/Build Operations")} 42 documents`,
          body: oGrid,
          acts: `${btn("Review the 4 new files", "p")}${btn("Pick up the cache review")}`,
        }) +
        `<div class="say">The cache proposal still has one open question: the timing baseline.</div>` +
        idle,
      cap: [
        "Reads the summary and picks where to start.",
        "Guidance in effect, document types with counts, conventions, the last recorded change and what changed since.",
        "No background watcher: new and moved files come from comparing the listing with the document-types file (B6); the last change from kb_list_edits.",
        'TheDriveAI scope panel (QOa4K8PSVl); mvp-proposal "Connect and orient/resume".',
      ],
    },
    {
      id: "O03",
      name: "If the folder has no guidance yet",
      h: 600,
      x: 1040,
      y: 820,
      content:
        oAsk +
        card({
          eb: "Knowledge base",
          title: "Field notes",
          meta: `${chip("folder", "~/Notes/Field notes")} 12 documents`,
          badge: badge("b-nt", "No guidance yet"),
          body: `<div class="note">${ic.info}<span>This folder has no definitions of its own, so the bundled guidance applies. Setting up your own lets each kind of document carry its own questions.</span></div>`,
          acts: `${btn("Set up guidance", "p")}${btn("Continue with bundled guidance", "g")}`,
        }) +
        idle,
      cap: [
        "Opens a folder with no .knowledge-bus.",
        "An honest empty state and two ways on.",
        "S1 bundled fallback; kb-ingest creates the definitions.",
        'mvp-proposal S1 "bundled fallback remains".',
      ],
    },
    {
      id: "O04",
      name: "If the guidance doesn’t validate",
      h: 640,
      x: 2080,
      y: 820,
      content:
        oAsk +
        card({
          eb: "Knowledge base",
          title: S,
          badge: badge("b-red", "Guidance has 2 problems", "warn"),
          body: tbl(
            ["Where", "Problem", "Fix"],
            [
              [
                `<span class="mono">product-dev › reader</span>`,
                "Element has no question",
                "Add the question it answers",
              ],
              [
                `<span class="mono">guidance › audience</span>`,
                "Keyed to an id that no longer exists",
                'Rekey it to <span class="mono">reader</span>',
              ],
            ],
          ),
          acts: `${btn("Fix with the assistant", "p")}${btn("Continue anyway", "g")}`,
        }) +
        idle,
      cap: [
        "Opens a folder whose definitions are broken.",
        "Each problem with where it is and the fix.",
        "kbp_validate refusals, translated.",
        "kb-check skill; kbp checker.",
      ],
    },
  ];

  // 02 Document
  const dAsk = user("Is this ready for review?", S);
  const dTrace = tool("kb_get_document_type", "Design proposal");
  const checks = `${tbl(
    ["Check", "In the document"],
    [
      [`${ic.ok} Motivation`, "7 of 9 evening runs hit the limit"],
      [
        `<span class="mu">${ic.left}</span> Alternatives`,
        '<span class="mu">Missing</span>',
      ],
      [`${ic.ok} Status`, "Proposed"],
      [`${ic.ok} Open questions`, "1 open: the timing baseline"],
    ],
  )}`;
  P["p02-document"] = [
    {
      id: "D01",
      name: "Document: type, reader and checks",
      h: 800,
      x: 0,
      y: 0,
      content:
        dAsk +
        dTrace +
        tool("kbp_card", "proposal structure and its guidance") +
        card({
          eb: "Document",
          title: "cache-proposal.md",
          meta: "Design proposal · from team guidance",
          body: sum([
            ["Reader", "Maintainers · accept or reject"],
            ["Guidance", "product-dev · Design proposal"],
            ["Checks", `3 of 4 met · <b>Alternatives missing</b>`],
            ["Still open", "Timing baseline"],
          ]),
          acts: `${btn("Bring in the meeting notes", "p")}`,
        }) +
        `<div class="say">Not yet: it has no alternatives section, and the timing baseline is still open. The Oct 27 meeting notes may settle the baseline; alternatives need your input.</div>` +
        idle,
      cap: [
        "Asks whether a document is ready.",
        "Its type, reader and which checks the document meets.",
        "kb_get_document_type, kbp_card; the assistant compares.",
        "Docs still km-still-2; mvp-proposal S1.",
      ],
    },
    {
      id: "D02",
      name: "If the type is unclear: one question",
      h: 620,
      x: 1040,
      y: 0,
      content:
        dAsk +
        tool("kb_get_document_type", "2 candidates") +
        card({
          eb: "Document",
          title: "build-review-notes.md",
          meta: "Two document types could fit",
          badge: badge("b-amb", "Your choice"),
          body:
            tbl(
              ["Type", "Why it might fit"],
              [
                ["Decision record", "States a decision and who made it"],
                ["Meeting notes", "Dated, with attendees and actions"],
              ],
            ) +
            `<div style="margin-top:12px">${`<span class="seg"><span class="on">Decision record</span><span>Meeting notes</span><span>Neither</span></span>`}</div>`,
          acts: `${btn("Use this type", "p")}`,
        }) +
        wait,
      cap: [
        "Asks about a file that fits two types.",
        "The candidates with the reason each might fit; one question.",
        "Candidates from kb_get_document_type; the choice is saved for later sessions (S3).",
        'mvp-proposal S1 "ask when unresolved".',
      ],
    },
    {
      id: "D03",
      name: "If no type fits",
      h: 600,
      x: 1040,
      y: 760,
      content:
        dAsk +
        tool("kb_get_document_type", "no type") +
        card({
          eb: "Document",
          title: "release-calendar.md",
          badge: badge("b-nt", "No type"),
          body: `<div class="note">${ic.left}<span>None of this folder’s 4 document types describes it. It stays as it is, and nothing is guessed.</span></div>`,
          acts: `${btn("Keep without a type", "p")}${btn("Propose a new type", "g")}`,
        }) +
        idle,
      cap: [
        "Asks about a file nothing describes.",
        'An explicit "No type", not a forced fit.',
        "No-fit is a real answer (S1); a new type goes to guidance change (08).",
        'mvp-proposal S1 "vendor no-fit".',
      ],
    },
    {
      id: "D04",
      name: "If the reader is a guess",
      h: 620,
      x: 2080,
      y: 760,
      content:
        dAsk +
        dTrace +
        card({
          eb: "Document",
          title: "deploy-runbook.md",
          meta: "Runbook · from team guidance",
          body: grid([
            [
              "Reader",
              'On-call engineers mid-incident <span class="badge b-amb">guess</span>',
            ],
            [
              "Why the guess",
              "Steps are numbered and written for a live outage",
            ],
          ]),
          acts: `${btn("Confirm reader", "p")}${btn("Choose another", "g")}`,
        }) +
        wait,
      cap: [
        "Opens a document whose reader isn’t recorded.",
        "The reader marked as a guess, with why.",
        "Guesses wait for confirmation, then persist (S2, S3).",
        'kb-write-document "(guess)" rule; mvp-proposal S2.',
      ],
    },
    {
      id: "D05",
      name: "New document: the summary inline",
      h: 1000,
      x: 0,
      y: 1560,
      content:
        user("Write a proposal for the cache rollout, on its own", S) +
        tool("kb_get_document_type", "Design proposal") +
        tool("kbp_card", "proposal structure") +
        tool("kb_list_audiences", "1 reader") +
        tool("kb_prepare_proposal", "C1–C3 · additions") +
        card({
          eb: "Proposed document",
          title: "Cache rollout",
          meta: `${chip("file", '<span class="mono">Proposals/cache-rollout.md</span>')} Design proposal · for maintainers <span class="badge b-nt">guess</span>`,
          badge: badge("b-amb", "Nothing saved"),
          full: true,
          body: sum([
            ["Sections", "C1 Motivation · C2 Alternatives · C3 Status"],
            ["Evidence", "1 supported · 1 partly answered · 1 suggested"],
            ["Saved as", "Proposals/cache-rollout.md · no naming rule"],
            ["Needs you", "Rollout owner · no source"],
          ]),
          acts: `${btn("Create the file", "p")}${btn("Not now", "g")}`,
        }) +
        wait,
      cap: [
        "Asks for a new document.",
        "Four data points: sections, evidence, where it goes and why, the one thing no source answers. The reader, a guess, sits in the meta line.",
        "kb_get_document_type, kbp_card, kb_list_audiences; kb_prepare_proposal draws the card, rows as additions; nothing written.",
        "kb-write-document steps 2–12; Claude design guidelines inline limits; amended recommendation 1.",
      ],
    },
    {
      id: "D05F",
      name: "Full view: each section and its sources",
      full: true,
      x: 1040,
      y: 1560,
      content: card({
        eb: "Proposed document",
        title: "Cache rollout",
        flat: true,
        meta: `${chip("file", '<span class="mono">Proposals/cache-rollout.md</span>')} Design proposal · for maintainers <span class="badge b-nt">reader is a guess</span>`,
        badge: badge("b-amb", "Nothing saved"),
        body:
          tbl(
            ["", "Section", "Draft", "Source"],
            [
              [
                cn(1),
                "Motivation",
                `${K.evTag("supported")}Cache misses add 40 minutes to each evening run`,
                `<span class="srcs">${f("build-timings.xlsx › Cache!B2:B9")}</span>`,
              ],
              [
                cn(2),
                "Alternatives",
                `${K.evTag("partly")}A hosted build service, priced but not compared`,
                `<span class="srcs">${f("vendor-quote.xlsx")}</span>`,
              ],
              [
                cn(3),
                "Status",
                `${K.evTag("suggested")}Proposed`,
                `<span class="srcs">${chip("note", "you: “a proposal … on its own”")}</span>`,
              ],
            ],
          ) +
          `<div class="note">${ic.info}<span><b>Design proposal has no naming rule</b> (dropped in conventions), so it goes beside cache-proposal.md.</span></div><div class="note">${ic.left}<span><b>One thing to answer.</b> Rollout owner · no source. It stays an open question unless you say.</span></div>`,
        acts: `${btn("Create the file", "p")}${btn("Not now", "g")}`,
      }),
      composer: wait,
      cap: [
        "Pressed Full view.",
        "Each section C1–C3 with its evidence mark and exact source.",
        "Same card instance in fullscreen; Create sends the message and returns inline.",
        "proposal.schema.yaml; vendor-quote.xlsx, left out of E02, answers here (Strategic Theme 2).",
      ],
    },
    {
      id: "D06",
      name: "Created and filed",
      h: 680,
      x: 2400,
      y: 1560,
      content:
        sent("Create Proposals/cache-rollout.md with C1–C3") +
        tool("kb_record_edit", "Proposals/cache-rollout.md created") +
        tool("kb_prepare_document_types", "document types updated") +
        card({
          eb: "Document",
          title: "Proposals/cache-rollout.md",
          meta: "Design proposal · recorded Oct 28, 10:12 · approved by you",
          badge: badge("b-grn", "Created", "check"),
          acts: `${btn("Undo", "", "undo")}${btn("Show the file", "g")}`,
        }) +
        `<div class="say">Created beside cache-proposal.md. Ownership is still an open question in the file.</div>` +
        idle,
      cap: [
        "Pressed Create the file.",
        "What was created, where, when and on whose OK; Undo.",
        "The assistant writes the file, records it, then updates the document-types file.",
        "kb-write-document Edits and kb-track-document-types; TheDriveAI applied card (huFTiG_YBS).",
      ],
    },
  ];

  // 04 Edit result
  const rHead = {
    eb: "Change",
    title: "cache-proposal.md · 4 changes",
    meta: "Recorded Oct 28, 09:41 · approved by you",
  };
  const diff = `<div class="diff"><div class="dm">Title: Build schedule and cache rollout</div><div class="dp">Title: Evening build retirement</div><div class="dm">Motivation: evening build never finishes</div><div class="dp">Motivation: 7 of 9 evening runs hit the 6-hour limit</div><div class="dp">Status: Proposed. Approval is disputed.</div><div class="dp">Still open: no timings from before the cache</div></div>`;
  P["p04-edit-result"] = [
    {
      id: "R01",
      name: "Saved, with Undo",
      h: 560,
      x: 0,
      y: 0,
      content:
        tool("kb_record_edit", "cache-proposal.md recorded") +
        card({
          ...rHead,
          badge: badge("b-grn", "Saved", "check"),
          acts: `${btn("Undo", "", "undo")}${btn("Show the change", "g")}`,
        }) +
        `<div class="say">Saved the four changes. The two questions are still open, so the status stays Proposed.</div>` +
        idle,
      cap: [
        "Sees the save land.",
        "A result card: what was saved, when, who approved it; Undo.",
        "kb_record_edit holds before and after.",
        "TheDriveAI result card (huFTiG_YBS); mvp-proposal S2.",
      ],
    },
    {
      id: "R02",
      name: "If you open the change",
      h: 640,
      x: 1040,
      y: 0,
      content:
        card({
          ...rHead,
          badge: badge("b-grn", "Saved", "check"),
          body: diff,
          acts: `${btn("Undo", "", "undo")}${`<span class="disc">Hide the change</span>`}`,
        }) + idle,
      cap: [
        "Opens Show the change.",
        "The exact before and after.",
        "From the edit record.",
        'TheDriveAI "Show the 1,264 changes" (huFTiG_YBS).',
      ],
    },
    {
      id: "R03",
      name: "If you undo",
      h: 600,
      x: 1040,
      y: 760,
      content:
        card({
          ...rHead,
          badge: badge("b-nt", "Undo requested"),
          body: '<div class="frozen">You asked to undo this.</div>',
        }) +
        sent("Undo the 09:41 edit to cache-proposal.md") +
        tool("kb_list_edits", "the file still holds what was written") +
        tool("kb_record_edit", "earlier text restored") +
        card({
          eb: "Change",
          title: "cache-proposal.md · 4 changes",
          meta: "Recorded Oct 28, 09:44 · undoes the 09:41 edit",
          badge: badge("b-grn", "Undone", "check"),
        }) +
        `<div class="say">cache-proposal.md is back to how it was before 09:41.</div>` +
        idle,
      cap: [
        "Presses Undo.",
        "The card freezes and sends the request; the undo arrives as a new card, its own recorded change.",
        "kb_list_edits confirms the file still holds the 09:41 text; the assistant restores it and records the undo.",
        "TheDriveAI undo as its own change (huFTiG_YBS); kb_list_edits restore rule.",
      ],
    },
    {
      id: "R04",
      name: "If undo isn’t safe anymore",
      h: 700,
      x: 2080,
      y: 760,
      content:
        card({
          ...rHead,
          badge: badge("b-nt", "Undo requested"),
          body: '<div class="frozen">You asked to undo this.</div>',
        }) +
        sent("Undo the 09:41 edit to cache-proposal.md") +
        tool("kb_list_edits", "2 later edits") +
        card({
          eb: "Change",
          title: "cache-proposal.md · 4 changes",
          badge: badge("b-red", "Can’t undo safely", "warn"),
          body: `<div class="note">${ic.warn}<span>cache-proposal.md changed after this edit (2 later edits). Undoing would overwrite them. Nothing was changed.</span></div>`,
          acts: `${btn("Show the later edits", "p")}`,
        }) +
        idle,
      cap: [
        "Presses Undo after later edits.",
        "The card freezes; a new card refuses, with the reason; nothing overwritten.",
        "kb_list_edits shows later edits; restore only where the file still holds what was written.",
        'knowledge-mcp edit-record rule (kb-write-document "Check or undo").',
      ],
    },
  ];

  // 05 Move plan
  const mHead = {
    eb: "Proposed moves",
    title: "File the new files",
    meta: `${chip("folder", "Inbox")} 4 new files`,
  };
  const mRows = tbl(
    ["File", "Goes to"],
    [
      [
        `<b>build-review-notes.md</b><div class="mu">Inbox</div>`,
        `Meetings/<div class="mu">as 2026-10-27 build review.md</div>`,
      ],
      [
        `<b>retire-evening.md</b><div class="mu">Inbox</div>`,
        `Decisions/<div class="mu">as 2026-10-28 retire evening build.md</div>`,
      ],
      [`<b>timings-notes.md</b><div class="mu">Inbox</div>`, `Proposals/`],
    ],
  );
  const mSum = (blocked) =>
    sum([
      ["Moves", "3 · Inbox → Meetings/, Decisions/, Proposals/"],
      ["Renames", "2 · date + title"],
      ["Links", "5 repaired · 4 notes"],
      ["Stays", "scan-0412.md · no document type"],
      ...(blocked
        ? [["Needs you", "<b>2 blockers</b> · name taken, ambiguous link"]]
        : []),
    ]);
  const mLeft = `<div class="note">${ic.left}<span><b>1 file stays where it is.</b> scan-0412.md has no document type.</span></div>`;
  const mWhy = `<span class="disc">${ic.link}Show the 5 links</span><div class="why">Waits for you because it moves files and edits links in 4 other notes. You can undo it afterwards.</div>`;
  P["p05-move-plan"] = [
    {
      id: "M01",
      name: "Plan: the summary inline",
      h: 760,
      x: 0,
      y: 0,
      content:
        user("Review the 4 new files", S) +
        tool("kb_prepare_document_moves", "3 moves · 5 links") +
        card({
          ...mHead,
          badge: badge("b-amb", "Needs your OK"),
          full: true,
          body:
            mSum(0) +
            `<div class="why">Waits for you because it moves files and edits links in 4 other notes. You can undo it afterwards.</div>`,
          acts: `${btn("Move 3 files", "p")}${btn("Not now", "g")}`,
        }) +
        wait,
      cap: [
        "Asks to file new arrivals.",
        "Four data points: what moves where, renames, links repaired, what stays and why. Full view lists each file and link.",
        "kb_prepare_document_moves; names from the folders already kept (B1) and conventions (B2).",
        "TheDriveAI proposal card (pSx_dSHMJl); Claude inline limits; amended recommendation 1.",
      ],
    },
    {
      id: "M03",
      name: "Approved: the card sends it, the assistant moves",
      h: 720,
      x: 1040,
      y: 0,
      content:
        card({
          ...mHead,
          eb: "Moves",
          badge: badge("b-grn", "Approved", "check"),
          body: mSum(0) + '<div class="frozen">You approved this.</div>',
        }) +
        sent("Move the 3 files and repair the 5 links") +
        tool("kb_prepare_document_moves", "prepared again with your OK") +
        tool("kb_record_edit", "5 of 8 writes recorded", 1) +
        busy,
      cap: [
        "Pressed Move 3 files.",
        "The plan freezes; its message goes to the assistant; the host’s step lines count the writes.",
        "The assistant prepares again with allowed_by, then writes 3 moves, 4 referring notes and the document-types file, recording each with kb_record_edit under one operation (index of 8). No progress card: the work spans many calls (recommendation 6).",
        'kb-write-document "Many files at once"; edit.schema.yaml operation index and count; TheDriveAI applying count (huFTiG_YBS).',
      ],
    },
    {
      id: "M04",
      name: "Moved, links checked",
      h: 600,
      x: 2080,
      y: 0,
      content:
        tool("kb_record_edit", "8 of 8 writes recorded · every link checked") +
        card({
          eb: "Moves",
          title: "File the new files",
          meta: "3 files · 5 links repaired and checked",
          badge: badge("b-grn", "Moved", "check"),
          acts: `${btn("Undo", "", "undo")}${btn("Show the moves", "g")}`,
        }) +
        `<div class="say">Filed. Every link to the moved files still opens the right note.</div>` +
        idle,
      cap: [
        "Sees the result.",
        "What moved, links repaired and verified; Undo.",
        "Every link target verified after the move (file-safety gate).",
        'TheDriveAI applied card (huFTiG_YBS); mvp-proposal "File safety".',
      ],
    },
    {
      id: "M02",
      name: "Full view: every move and link",
      full: true,
      x: 0,
      y: 900,
      content: card({
        ...mHead,
        flat: true,
        badge: badge("b-amb", "Needs your OK"),
        body:
          `<div class="tabs"><span class="on">Moves (3)</span><span>Links (5)</span></div>` +
          mRows +
          mLeft +
          `<div class="tabs" style="margin-top:22px"><span>Moves (3)</span><span class="on">Links (5)</span></div>` +
          tbl(
            ["Note", "Link now", "After the move"],
            [
              [
                f("decisions-index.md:12"),
                '<span class="mono">[[retire-evening]]</span>',
                '<span class="mono">[[2026-10-28 retire evening build]]</span>',
              ],
              [
                f("cache-proposal.md:40"),
                '<span class="mono">[[timings-notes]]</span>',
                '<span class="mono">[[Proposals/timings-notes]]</span>',
              ],
              [
                f("weekly-2026-43.md:7"),
                '<span class="mono">[[build-review-notes]]</span>',
                '<span class="mono">[[2026-10-27 build review]]</span>',
              ],
              ['<span class="mu">+ 2 more</span>', "", ""],
            ],
          ),
        acts: `${btn("Move 3 files", "p")}${btn("Not now", "g")}`,
      }),
      composer: wait,
      cap: [
        "Pressed Full view.",
        "Two tabs: each file with where it goes and its new name, and each link before and after. Both tabs are shown here.",
        "Same card instance in fullscreen; tabs instead of floating panels (Claude full-screen rule).",
        'kb-write-document "Names, folders and moves"; Claude design guidelines full screen.',
      ],
    },
    {
      id: "M05",
      name: "If the plan has blockers",
      h: 580,
      x: 1360,
      y: 900,
      content:
        user("Review the 4 new files", S) +
        tool("kb_prepare_document_moves", "2 blockers") +
        card({
          ...mHead,
          badge: badge("b-amb", "Needs your choice"),
          full: true,
          body:
            mSum(1) +
            `<div class="why">Move stays off until each blocker has a choice: open the full view.</div>`,
          acts: `${btn("Move 3 files", "p dis")}${btn("Not now", "g")}`,
        }) +
        wait,
      cap: [
        "Asks to file new arrivals; the plan finds blockers.",
        "The summary names the 2 blockers; Move stays off until they are answered in the full view.",
        "Collisions and ambiguous links are resolved before approval, then the plan is prepared again.",
        'mvp-proposal "File safety"; kb-write-document move rules.',
      ],
    },
    {
      id: "M05F",
      name: "Full view: answer the blockers",
      full: true,
      x: 2400,
      y: 900,
      content: card({
        ...mHead,
        flat: true,
        badge: badge("b-amb", "Needs your choice"),
        body:
          tbl(
            ["Problem", "Your choice"],
            [
              [
                `<b>Decisions/2026-10-28 retire evening build.md</b> already exists`,
                `<span class="tick"><span class="cb off"></span>Skip this file</span>`,
              ],
              [
                `<span class="mono">[[proposal]]</span> in weekly-2026-43.md matches 2 notes`,
                `<span class="seg"><span>Link to Proposals/cache-proposal</span><span>Link to Proposals/timings-notes</span></span>`,
              ],
            ],
          ) +
          `<div class="why">Move stays off until each blocker has a choice. To keep both under a new name, say the name in chat.</div>`,
        acts: `${btn("Move 3 files", "p dis")}${btn("Not now", "g")}`,
      }),
      composer: wait,
      cap: [
        "Pressed Full view to answer the blockers.",
        "Each blocker with a visible choice; Move stays off until all are answered.",
        "Choices come from the plan (skip_move, bind_link): one choice is a tick, two or three a segmented choice. Keeping both needs a new name, which is words, so it goes in chat.",
        "Claude design guidelines: visible controls, text in chat.",
      ],
    },
    {
      id: "M06",
      name: "If you choose Not now",
      h: 640,
      x: 2080,
      y: 900,
      content:
        card({
          ...mHead,
          badge: badge("b-nt", "Not moved"),
          body: mSum(0) + '<div class="frozen">Not moved.</div>',
        }) +
        sent("Not now") +
        `<div class="say">Nothing moved. Tell me what to change, for example keep the original names, and I’ll plan it again.</div>` +
        idle,
      cap: [
        "Presses Not now.",
        'The plan freezes as "Not moved." and tells the assistant',
        "No change, no record.",
        "TheDriveAI Not now (oC4ZORjRov).",
      ],
    },
  ];

  // 06 Conventions
  const dec = `<span class="seg"><span>Accept</span><span>Drop</span></span>`;
  const cRows = (meet, acc) =>
    tbl(
      ["Document type", "Folder", "Name", "Example", ""],
      [
        [
          "Decision record",
          "Decisions/",
          "date · title",
          '<span class="mono">Decisions/2026-10-28 retire evening build.md</span>',
          acc ? badge("b-grn", "Accepted", "check") : dec,
        ],
        [
          "Meeting notes",
          meet,
          "date · title",
          `<span class="mono">${meet}2026-10-27 build review.md</span>`,
          acc
            ? badge("b-grn", "Accepted", "check")
            : meet !== "Meetings/"
              ? badge("b-nt", "Changed")
              : dec,
        ],
        [
          "Design proposal",
          "Proposals/",
          "title",
          '<span class="mono">Proposals/timings-notes.md</span>',
          acc ? badge("b-nt", "Dropped") : dec,
        ],
      ],
    );
  const cSum = (meet, state) =>
    sum([
      [
        "Decision record",
        `Decisions/ · date · title${state === "saved" ? " · <b>accepted</b>" : ""}`,
      ],
      [
        "Meeting notes",
        `${meet} · date · title${state === "saved" ? " · <b>accepted</b>" : meet !== "Meetings/" ? " · <b>changed</b>" : ""}`,
      ],
      [
        "Design proposal",
        `Proposals/ · title${state === "saved" ? " · <b>dropped</b>" : ""}`,
      ],
      ["Existing files", "Unchanged until a move"],
    ]);
  P["p06-conventions"] = [
    {
      id: "C01",
      name: "Proposed conventions: the summary inline",
      h: 700,
      x: 0,
      y: 0,
      content:
        user("Suggest naming rules for this folder", S) +
        tool("kb_prepare_conventions", "3 proposals") +
        card({
          eb: "Proposed conventions",
          title: `Naming and filing for ${S}`,
          meta: "Drawn from the folders you already keep",
          badge: badge("b-amb", "Nothing saved"),
          full: true,
          body: cSum("Meetings/"),
          acts: `${btn("Save all 3", "p")}${btn("Not now", "g")}`,
        }) +
        wait,
      cap: [
        "Asks for naming rules.",
        "One line per document type: folder and name; existing files untouched. Accept or drop each in the full view.",
        "kb_prepare_conventions (B2, B3).",
        "kb-write-document Templates and Conventions; Claude inline limits.",
      ],
    },
    {
      id: "C01F",
      name: "Full view: accept or drop each",
      full: true,
      x: 1040,
      y: 0,
      content: card({
        eb: "Proposed conventions",
        title: `Naming and filing for ${S}`,
        flat: true,
        meta: "Drawn from the folders you already keep",
        badge: badge("b-amb", "Nothing saved"),
        body:
          cRows("Meetings/", 0) +
          `<div class="why">Existing files Unchanged until a move. To change a folder or name, say it in chat.</div>`,
        acts: `${btn("Save accepted", "p")}${btn("Not now", "g")}`,
      }),
      composer: wait,
      cap: [
        "Pressed Full view.",
        "Each proposal with a rendered example and Accept | Drop.",
        "Choices are selections; changing a value goes through chat and prepares again (C02).",
        "kb-write-document “show a rendered example”; Claude visible controls.",
      ],
    },
    {
      id: "C02",
      name: "If you change a row",
      h: 700,
      x: 2400,
      y: 0,
      content:
        user("Put meeting notes under Calendar/Meetings/", S) +
        tool("kb_prepare_conventions", "prepared again") +
        card({
          eb: "Proposed conventions",
          title: `Naming and filing for ${S}`,
          badge: badge("b-amb", "Nothing saved"),
          full: true,
          body: cSum("Calendar/Meetings/"),
          acts: `${btn("Save all 3", "p")}${btn("Not now", "g")}`,
        }) +
        wait,
      cap: [
        "Changes the folder for one row.",
        "The example re-renders with the new folder.",
        "The changed proposal is checked again before saving.",
        'kb-write-document "show a rendered example".',
      ],
    },
    {
      id: "C03",
      name: "Saved",
      h: 760,
      x: 3440,
      y: 0,
      content:
        sent("Save the accepted conventions; drop Design proposal") +
        tool("kb_prepare_conventions", "prepared with your OK") +
        tool("kb_record_edit", "conventions.yaml recorded") +
        card({
          eb: "Conventions",
          title: `Naming and filing for ${S}`,
          meta: "2 conventions saved · 1 dropped",
          badge: badge("b-grn", "Saved", "check"),
          body: cSum("Calendar/Meetings/", "saved"),
          acts: `${btn("Undo", "", "undo")}${btn("Propose moves for existing files", "g")}`,
        }) +
        idle,
      cap: [
        "Saved the accepted rows.",
        "What was saved and dropped; next step offered, not taken.",
        "Conventions file written and recorded; files unchanged.",
        'kb-write-document "Saving conventions leaves note paths unchanged".',
      ],
    },
  ];

  // 07 History
  P["p07-history"] = [
    {
      id: "H01",
      name: "History: the summary inline",
      h: 720,
      x: 0,
      y: 0,
      content:
        user("What changed this week?", S) +
        tool("kb_list_edits", "5 changes") +
        card({
          eb: "History",
          title: `${S} · last 7 days`,
          full: true,
          body:
            sum([
              ["Changes", "5 · 3 today, 1 yesterday, 1 by you"],
              ["Latest", "2 conventions saved · Oct 28, 10:03"],
              ["Can undo", "3 · deploy-runbook.md changed since"],
            ]) +
            `<div class="why">To undo one, say which in chat, for example “undo the move”.</div>`,
        }) +
        idle,
      cap: [
        "Asks what changed.",
        "Three data points: how many and by whom, the latest, what can still be undone. The list is in the full view.",
        "kb_list_edits; undo only where the file still holds what was written.",
        "TheDriveAI Activity (QOa4K8PSVl); Claude inline limits.",
      ],
    },
    {
      id: "H01F",
      name: "Full view: every change",
      full: true,
      x: 1040,
      y: 0,
      content: card({
        eb: "History",
        title: `${S} · last 7 days`,
        flat: true,
        body:
          tbl(
            ["Change", "When", "Who", ""],
            [
              [
                "<b>Saved</b> 2 conventions",
                "Oct 28, 10:03",
                "Assistant · for you",
                '<span class="mu">Can undo</span>',
              ],
              [
                "<b>Moved</b> 3 files · 5 links repaired",
                "Oct 28, 09:52",
                "Assistant · for you",
                '<span class="mu">Can undo</span>',
              ],
              [
                "<b>Revised</b> cache-proposal.md · 4 changes",
                "Oct 28, 09:41",
                "Assistant · for you",
                '<span class="mu">Can undo</span>',
              ],
              [
                "<b>Revised</b> deploy-runbook.md · 2 changes",
                "Oct 27, 16:20",
                "Assistant · for you",
                '<span class="mu">Changed later</span>',
              ],
              [
                "<b>Undid</b> a revision to cache-policy.md",
                "Oct 26, 11:05",
                "You",
                "",
              ],
            ],
          ) + `<div class="why">To undo one, say which in chat.</div>`,
      }),
      composer: idle,
      cap: [
        "Pressed Full view.",
        "Each change: verb, item, when, who made it and who it was for, and whether it can still be undone.",
        "Same card in fullscreen; undo goes through chat (one action per change would exceed the card’s two).",
        "kb_list_edits; TheDriveAI Activity (QOa4K8PSVl).",
      ],
    },
    {
      id: "H02",
      name: "If nothing is recorded yet",
      h: 480,
      x: 2400,
      y: 0,
      content:
        user("What changed this week?", "Field notes") +
        tool("kb_list_edits", "none") +
        card({
          eb: "History",
          title: "Field notes",
          badge: badge("b-nt", "Nothing yet"),
          body: '<div class="why">Changes you approve show up here, with who made them and how to undo them.</div>',
        }) +
        comp("Field notes", "Ask about Field notes"),
      cap: [
        "Asks in a folder with no history.",
        "A plain empty state.",
        "No records.",
        'TheDriveAI Activity empty counterpart; mvp-proposal "Records and help".',
      ],
    },
  ];

  // 08 Guidance change
  const gRows = (done) =>
    tbl(
      ["#", "Where", "Current", "Proposed", "Evidence", ""],
      [
        [
          "1",
          '<span class="mono">Design proposal › rollback</span>',
          "new",
          "What happens if this is reversed?",
          "4 of 6 proposals added one by hand",
          done
            ? badge("b-grn", "Applied", "check")
            : `<span class="seg"><span class="on">Apply</span><span>Skip</span></span>`,
        ],
        [
          "2",
          '<span class="mono">guidance › rollback · empty</span>',
          "new",
          "An honest empty answer says no rollback is possible",
          "kb-evolve rule: every new element gets one",
          done
            ? badge("b-grn", "Applied", "check")
            : `<span class="seg"><span class="on">Apply</span><span>Skip</span></span>`,
        ],
        [
          "3",
          '<span class="mono">Design proposal › cost</span>',
          "new",
          '<span class="mu">no change</span>',
          "refused: 1 proposal only",
          done
            ? badge("b-nt", "Refused")
            : `<span class="seg"><span>Apply</span><span class="on">Keep refused</span></span>`,
        ],
      ],
    );
  P["p08-guidance"] = [
    {
      id: "G01",
      name: "Proposed guidance change: the summary inline",
      h: 760,
      x: 0,
      y: 0,
      content:
        user(
          "Proposals keep adding a rollback section by hand. Should the guidance ask for it?",
          S,
        ) +
        card({
          eb: "Proposed guidance change",
          title: "Design proposal: ask for a rollback plan",
          meta: "Team guidance · product-dev",
          badge: badge("b-amb", "Nothing saved"),
          full: true,
          body: sum([
            ["Applies", "2 · rollback question, empty-answer guidance"],
            ["Refused", "1 · cost section, 1 proposal only"],
            ["Evidence", "Rollback added by hand in 4 of 6 proposals"],
            ["Effect", "Every Design proposal checked · v1.3 → 1.4"],
          ]),
          acts: `${btn("Apply 2 changes", "p")}${btn("Not now", "g")}`,
        }) +
        wait,
      cap: [
        "Asks whether guidance should change.",
        "Four data points: what applies, what was refused and why, the evidence, the effect.",
        "kb-evolve change table, summarised; each row in the full view.",
        'kb-evolve "The change table"; Claude inline limits.',
      ],
    },
    {
      id: "G01F",
      name: "Full view: the change table",
      full: true,
      x: 1040,
      y: 0,
      content: card({
        eb: "Proposed guidance change",
        title: "Design proposal: ask for a rollback plan",
        flat: true,
        meta: "Team guidance · product-dev · evidence from 6 proposals",
        badge: badge("b-amb", "Nothing saved"),
        body:
          gRows(0) +
          `<div class="why">Changes how every Design proposal is checked from now on. The version goes from 1.3 to 1.4.</div>`,
        acts: `${btn("Apply 2 changes", "p")}${btn("Not now", "g")}`,
      }),
      composer: wait,
      cap: [
        "Pressed Full view.",
        "Each change with where, current, proposed and evidence; Apply | Skip per row; the refusal kept visible.",
        "kb-evolve change table; nothing written until each row is answered.",
        'kb-evolve "The change table"; mvp-proposal "Improve reusable guidance from evidence".',
      ],
    },
    {
      id: "G02",
      name: "Applied and validated",
      h: 800,
      x: 2400,
      y: 0,
      content:
        sent("Apply changes 1 and 2; keep 3 refused") +
        tool("kbp_validate", "passed") +
        card({
          eb: "Guidance changed",
          title: "Design proposal: ask for a rollback plan",
          meta: "Version 1.4 · checker passed · recorded in evolve-log.md",
          badge: badge("b-grn", "Applied", "check"),
          body: sum([
            ["Applied", "2"],
            ["Refused", "1"],
            ["Checker", "Passed"],
            ["Recorded", "evolve-log.md"],
          ]),
          acts: `${btn("Check cache-proposal.md again", "p")}${btn("Undo", "", "undo")}`,
        }) +
        idle,
      cap: [
        "Applied the rows.",
        "What changed, the new version, the checker result; a next step to see its effect.",
        "Files written, kbp validates, the decision is logged.",
        'kb-evolve steps 10–11; mvp-proposal acceptance "reload; effect on a second document".',
      ],
    },
    {
      id: "G03",
      name: "If the checker refuses it",
      h: 600,
      x: 2400,
      y: 1000,
      content:
        card({
          eb: "Proposed guidance change",
          title: "Design proposal: ask for a rollback plan",
          badge: badge("b-red", "Checker refused", "warn"),
          body: `<div class="note">${ic.warn}<span><span class="mono">kbp: element 'rollback' has no question</span><br>Each element needs the question it answers. Nothing was saved.</span></div>`,
          acts: `${btn("Fix and try again", "p")}${btn("Not now", "g")}`,
        }) + wait,
      cap: [
        "Applies a change that doesn’t validate.",
        "The checker’s refusal and what it means; nothing saved.",
        "kbp_validate before writing.",
        "kb-check; kb-evolve step 10.",
      ],
    },
  ];
  window.FLOWS_REST = P;
})();
("ok");
