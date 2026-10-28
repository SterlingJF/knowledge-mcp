import { useState } from "react";

import { badge } from "@/copy/en";

import { countAccepted, DecisionRows } from "./decision-rows";
import type { DecisionKind, DecisionValue } from "./decision-rows";

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
  initial: Record<string, DecisionValue>;
}) {
  const [choices, setChoices] =
    useState<Record<string, DecisionValue | null>>(initial);
  return (
    <div>
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

export default {
  id: "P04",
  name: "Decision rows",
  stories: {
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
  },
};
