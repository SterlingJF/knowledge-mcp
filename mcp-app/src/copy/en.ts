// Every user-facing string in the app, from F07 Copy and terms on the storyboard.
// Summary values are terse noun phrases joined by " · ": no articles, semicolons or colons inside a value.

export const badge = {
  waiting: {
    needsOk: "Needs your OK",
    nothingSaved: "Nothing saved",
    yourChoice: "Your choice",
    needsChoice: "Needs your choice",
  },
  done: {
    saved: "Saved",
    approved: "Approved",
    created: "Created",
    moved: "Moved",
    applied: "Applied",
    undone: "Undone",
    accepted: "Accepted",
  },
  refused: { cantUndo: "Can’t undo safely", checkerRefused: "Checker refused" },
  neutral: {
    notSaved: "Not saved",
    notMoved: "Not moved",
    noType: "No type",
    noGuidance: "No guidance yet",
    nothingYet: "Nothing yet",
    undoRequested: "Undo requested",
    replaced: "Replaced",
    dropped: "Dropped",
  },
} as const;

export const frozen = {
  approved: "You approved this.",
  notSaved: "Not saved.",
  notMoved: "Not moved.",
  undoRequested: "You asked to undo this.",
  replaced: "Replaced by the card below.",
} as const;

export const action = {
  notNow: "Not now",
  undo: "Undo",
  prepareAgain: "Prepare again",
  fullView: "Full view",
  showWhy: "Show why",
  createFile: "Create the file",
  showChange: "Show the change",
  showLaterEdits: "Show the later edits",
  all: "All",
  save: (changes: string) => `Save ${changes}`,
  move: (count: number) => `Move ${count} ${count === 1 ? "file" : "files"}`,
  apply: (count: number) =>
    `Apply ${count} ${count === 1 ? "change" : "changes"}`,
} as const;

export const decision = {
  accept: "Accept",
  drop: "Drop",
  apply: "Apply",
  skip: "Skip",
  keepRefused: "Keep refused",
} as const;

/** Evidence marks as they read inside a summary count: `1 partly answered`. */
export const evidenceCount = {
  supported: "supported",
  partly: "partly answered",
  conflicting: "conflicting",
  suggested: "suggested",
} as const;

export const evidence = {
  supported: "Supported",
  partly: "Partly answered",
  conflicting: "Conflicting",
  suggested: "Suggested",
} as const;

export const line = {
  waitsBecause: (file: string) =>
    `Waits for you because it changes ${file}. Every saved edit is recorded and can be undone.`,
  leftOut: (count: number) =>
    count === 0
      ? "Nothing left out"
      : `${count} ${count === 1 ? "file" : "files"} left out`,
  addition: "— addition",
  /** Stands in for the file name when a result names no document. */
  theDocument: "the document",
  /** After the first item of a list cut short inline: `C3 Status · … · +1 more`. */
  andMore: (count: number) => `+${count} more`,
  /** Every refusal says this after its reason (F07). */
  nothingChanged: "Nothing was changed.",
  summaryJoin: " · ",
} as const;

export const source = {
  you: "you",
  /** Between two places in one file that disagree: `meeting-notes.md:11 vs :19`. */
  versus: "vs",
  /** A line in a text file: `meeting-notes.md:15`. */
  line: (file: string, lineNumber: number) => `${file}:${lineNumber}`,
  /** Another line in the same file, after a chip that named it. */
  sameFile: (lineNumber: number) => `:${lineNumber}`,
  /** A place in a sheet or deck: `build-timings.xlsx › Evening!A2:D10`. */
  place: (file: string, place: string) => `${file} › ${place}`,
  /** The person's words in this conversation. */
  said: (text: string) => `you: “${text}”`,
} as const;

export const change = {
  /** The contract's name for proposal row n. */
  number: (n: number) => `C${n}`,
  range: (from: number, to: number) =>
    from === to ? `C${from}` : `C${from}–C${to}`,
  /** More changes than a summary line can name: `6 changes`. */
  count: (n: number) => `${n} ${n === 1 ? "change" : "changes"}`,
  /** Change numbers as runs: [1,2,3,4] → "C1–C4"; [1,3,4] → "C1, C3–C4". */
  list: (numbers: Array<number>) =>
    numbers
      .slice()
      .sort((a, b) => a - b)
      .reduce<Array<[number, number]>>((runs, n) => {
        const last = runs.at(-1);
        if (last && n === last[1] + 1) last[1] = n;
        else runs.push([n, n]);
        return runs;
      }, [])
      .map(([from, to]) => (from === to ? `C${from}` : `C${from}–C${to}`))
      .join(", "),
} as const;

export const status = {
  loading: "Loading",
} as const;

export const meta = {
  /** Result-card meta: `Recorded Oct 28, 09:41 · approved by you`. */
  recorded: (when: string) => `Recorded ${when}`,
  approvedByYou: "approved by you",
  join: " · ",
} as const;

export const eyebrow = {
  proposedChanges: "Proposed changes",
  proposedDocument: "Proposed document",
  change: "Change",
} as const;

/** What a card's button sends as the person's message. */
export const message = {
  save: (changes: string, file: string, leftOut?: string) =>
    `Save ${changes} to ${file}${leftOut ? `; leave out ${leftOut}` : ""}`,
  create: (file: string, changes: string) => `Create ${file} with ${changes}`,
  notNow: "Not now",
} as const;

export const label = {
  changes: "Changes",
  sections: "Sections",
  savedAs: "Saved as",
  evidence: "Evidence",
  needsYou: "Needs you",
  leftOut: "Left out",
  unchanged: "Unchanged",
  current: "Current",
  proposed: "Proposed",
  source: "Source",
} as const;
