import { useState } from "react";

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

const blockers: DecisionRow[] = [
  {
    id: "name",
    name: "Name taken",
    cells: [
      mono("timings-notes.md"),
      "Proposals/timings-notes.md already exists",
    ],
    options: [
      { value: "rename", label: "Rename to timings-notes-2.md" },
      { value: "replace", label: "Replace the existing file" },
      { value: "skip", label: "Skip this file" },
    ],
  },
  {
    id: "link",
    name: "Ambiguous link",
    cells: [mono("weekly-2026-43.md:7"), mono("[[build review]]")],
    options: [
      {
        value: "a",
        label: "Link to Decisions/2026-10-28 retire evening build",
      },
      {
        value: "b",
        label: "Link to Calendar/Meetings/2026-10-27 build review",
      },
    ],
  },
  {
    id: "scan",
    name: "No document type",
    cells: [mono("scan-0412.md"), "No document type"],
    options: [{ value: "skip", label: "Skip this file" }],
  },
];

function Blockers() {
  const [choices, setChoices] = useState<Record<string, string | null>>({});
  return (
    <div className="@container">
      <DecisionRows
        headers={["File", "Blocker"]}
        rows={blockers}
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
    "Move blockers at 727px": (
      <div className="w-[727px] max-w-full">
        <Blockers />
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
