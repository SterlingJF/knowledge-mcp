import { badge } from "@/copy/en";

import { DecisionRows } from "./decision-rows";

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

export default {
  id: "P04",
  name: "Decision rows",
  stories: {
    Undecided: (
      <DecisionRows
        headers={headers}
        rows={base}
        choices={{ mn: "accept", dp: "drop" }}
        onChoiceChange={noop}
      />
    ),
    "Apply or keep refused": (
      <DecisionRows
        headers={headers}
        rows={base}
        kind="applyKeepRefused"
        choices={{ dr: "apply" }}
        onChoiceChange={noop}
      />
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
