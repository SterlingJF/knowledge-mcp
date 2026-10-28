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
    `${count} ${count === 1 ? "file" : "files"} left out`,
  addition: "— addition",
  summaryJoin: " · ",
} as const;

export const source = {
  you: "you",
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
} as const;

export const status = {
  loading: "Loading",
} as const;

export const label = {
  changes: "Changes",
  evidence: "Evidence",
  needsYou: "Needs you",
  leftOut: "Left out",
  unchanged: "Unchanged",
  current: "Current",
  proposed: "Proposed",
  source: "Source",
} as const;
