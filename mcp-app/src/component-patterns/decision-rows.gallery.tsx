import { useState } from "react";
import type { ReactNode } from "react";

import { badge } from "@/copy/en";

import { countAccepted, DecisionRows } from "./decision-rows";
import type { DecisionKind, DecisionRow } from "./decision-rows";

const mono = (t: string) => (
  <span className="font-(family-name:--font-mono)">{t}</span>
);
const base = [
  {
    id: "dr",
    name: "Decision record",
    cells: [
      "Decision record",
      "Decisions/",
      mono("Decisions/2026-10-28 retire evening build.md"),
    ],
  },
  {
    id: "mn",
    name: "Meeting notes",
    cells: [
      "Meeting notes",
      "Calendar/Meetings/",
      mono("Calendar/Meetings/2026-10-27 build review.md"),
    ],
  },
  {
    id: "dp",
    name: "Design proposal",
    cells: [
      "Design proposal",
      "Proposals/",
      mono("Proposals/timings-notes.md"),
    ],
  },
];
const headers = ["Document type", "Folder", "Example"];
const noop = () => {};

function Live({
  kind,
  initial,
}: {
  kind?: DecisionKind;
  initial: Record<string, string>;
}) {
  const [choices, setChoices] =
    useState<Record<string, string | null>>(initial);
  return (
    <div className="@container">
      <DecisionRows
        headers={headers}
        rows={base}
        kind={kind}
        choices={choices}
        onChoiceChange={(id, v) => setChoices({ ...choices, [id]: v })}
      />
      <p className="text-(length:--font-text-xs-size) text-(--color-text-tertiary)">
        {countAccepted(choices)} / {base.length}
      </p>
    </div>
  );
}

// M05F: one Problem cell per blocker, then its choice.
const blockers: DecisionRow[] = [
  {
    id: "exists",
    name: "Name taken",
    cells: [
      <span>
        <b className="font-(--font-weight-semibold)">
          Decisions/2026-10-28 retire evening build.md
        </b>{" "}
        already exists
      </span>,
    ],
    options: [{ value: "skip", label: "Skip this file" }],
  },
  {
    id: "link",
    name: "Ambiguous link",
    cells: [
      <span>{mono("[[proposal]]")} in weekly-2026-43.md matches 2 notes</span>,
    ],
    options: [
      { value: "a", label: "Link to Proposals/cache-proposal" },
      { value: "b", label: "Link to Proposals/timings-notes" },
    ],
  },
  {
    id: "long",
    name: "Ambiguous link",
    cells: [
      <span>
        {mono("[[build review]]")} in weekly-2026-43.md matches 3 notes
      </span>,
    ],
    options: [
      {
        value: "a",
        label: "Link to Decisions/2026-10-28 retire evening build",
      },
      {
        value: "b",
        label: "Link to Calendar/Meetings/2026-10-27 build review",
      },
      { value: "c", label: "Link to Proposals/timings-notes" },
    ],
  },
  {
    id: "notype",
    name: "No document type",
    cells: [
      <span>
        <b className="font-(--font-weight-semibold)">scan-0412.md</b> has no
        document type
      </span>,
    ],
    options: [],
  },
];

const problem = (file: string, rest: string) => (
  <span>
    <b className="font-(--font-weight-semibold)">{file}</b> {rest}
  </span>
);
const onlyInChat: DecisionRow[] = [
  {
    id: "a",
    name: "No type",
    cells: [problem("scan-0412.md", "has no document type")],
    options: [],
  },
  {
    id: "b",
    name: "No type",
    cells: [problem("whiteboard.png", "has no document type")],
    options: [],
  },
];
const mixed: DecisionRow[] = [
  {
    id: "c",
    name: "Name taken",
    cells: [
      problem("Decisions/2026-10-28 retire evening build.md", "already exists"),
    ],
    options: [{ value: "skip", label: "Skip this file" }],
  },
  onlyInChat[0],
];

function Answers({ rows }: { rows: DecisionRow[] }) {
  return (
    <div className="@container">
      <DecisionRows
        headers={["Problem", "Your choice"]}
        rows={rows}
        narrow={{}}
        align="start"
        onChoiceChange={() => {}}
      />
    </div>
  );
}

const widths = ["816", "727", "360", "320"] as const;
const sized = (w: (typeof widths)[number], node: ReactNode) => (
  <div style={{ width: `${w}px` }} className="max-w-full">
    {node}
  </div>
);
const answerStories = Object.fromEntries(
  widths.flatMap((w) => [
    [`Only answer in chat at ${w}px`, sized(w, <Answers rows={onlyInChat} />)],
    [
      `Tick box and answer in chat at ${w}px`,
      sized(w, <Answers rows={mixed} />),
    ],
  ]),
);

function Blockers() {
  const [choices, setChoices] = useState<Record<string, string | null>>({});
  return (
    <div className="@container">
      <DecisionRows
        headers={["Problem", "Your choice"]}
        rows={blockers}
        narrow={{}}
        align="start"
        choices={choices}
        onChoiceChange={(id, v) => setChoices({ ...choices, [id]: v })}
      />
    </div>
  );
}

export default {
  id: "P04",
  name: "Decision rows",
  stories: {
    ...answerStories,
    "Move blockers at 727px": (
      <div className="w-[727px] max-w-full">
        <Blockers />
      </div>
    ),
    "Move blockers at 816px": (
      <div className="w-[816px] max-w-full">
        <Blockers />
      </div>
    ),
    "Move blockers at 320px": (
      <div className="w-[320px] max-w-full">
        <Blockers />
      </div>
    ),
    "Conventions at 816px": (
      <div className="w-[816px] max-w-full">
        <Live initial={{ mn: "accept", dp: "drop" }} />
      </div>
    ),
    "Conventions at 727px": (
      <div className="w-[727px] max-w-full">
        <Live initial={{ mn: "accept", dp: "drop" }} />
      </div>
    ),
    "Conventions at 360px": (
      <div className="w-[360px] max-w-full">
        <Live initial={{ mn: "accept", dp: "drop" }} />
      </div>
    ),
    "Conventions at 320px": (
      <div className="w-[320px] max-w-full">
        <Live initial={{ mn: "accept", dp: "drop" }} />
      </div>
    ),
    "Move blockers at 360px": (
      <div className="w-[360px] max-w-full">
        <Blockers />
      </div>
    ),
    Undecided: <Live initial={{ mn: "accept", dp: "drop" }} />,
    "Apply or keep refused": (
      <Live kind="applyKeepRefused" initial={{ dr: "apply" }} />
    ),
    Decided: (
      <DecisionRows
        headers={headers}
        rows={base.map((r) => ({
          ...r,
          decided:
            r.id === "dp"
              ? { tone: "neutral" as const, label: badge.neutral.dropped }
              : { tone: "done" as const, label: badge.done.accepted },
        }))}
        choices={{}}
        onChoiceChange={noop}
      />
    ),
    "Undecided at 360px": (
      <div className="w-[360px]">
        <Live initial={{ mn: "accept", dp: "drop" }} />
      </div>
    ),
    "Undecided at 320px": (
      <div className="w-[320px]">
        <Live initial={{ mn: "accept" }} />
      </div>
    ),
  },
};
