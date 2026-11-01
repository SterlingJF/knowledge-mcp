import { useState } from "react";

import type { ProposalRow } from "@/contracts/proposal";

import { ChangeTable } from "./change-table";

const rows: ProposalRow[] = [
  {
    current: { label: "Title", text: "Build schedule and cache rollout" },
    proposed: { label: "Title", text: "Evening build retirement" },
    mark: "suggested",
    sources: [{ file: "meeting-notes.md", line_number: 15 }],
  },
  {
    current: { label: "Motivation", text: "evening build never finishes" },
    proposed: {
      label: "Motivation",
      text: "7 of 9 evening runs hit the 6-hour limit",
    },
    mark: "supported",
    sources: [{ file: "build-timings.xlsx", place: "Evening!A2:D10" }],
  },
  {
    proposed: { label: "Owner", text: "Platform team" },
    mark: "conflicting",
    sources: [
      { file: "meeting-notes.md", line_number: 12 },
      { file: "meeting-notes.md", line_number: 19 },
    ],
  },
];

function Live({ initial }: { initial: number[] }) {
  const [kept, setKept] = useState(new Set(initial));
  return <ChangeTable rows={rows} kept={kept} onKeptChange={setKept} />;
}

// Wide enough for the four-column layout.
const wide = "@container w-190 max-w-full";

export default {
  id: "P02",
  name: "Change table",
  stories: {
    "Some left out": (
      <div className={wide}>
        <Live initial={[1, 3]} />
      </div>
    ),
    Frozen: (
      <div className={wide}>
        <ChangeTable rows={rows} />
      </div>
    ),
    "Full view at 727px": (
      <div className="@container w-181.75 max-w-full">
        <Live initial={[1, 2, 3]} />
      </div>
    ),
    "Draft at 727px": (
      <div className="@container w-181.75 max-w-full">
        <ChangeTable rows={rows} draft />
      </div>
    ),
    "Frozen, C1 left out": (
      <div className={wide}>
        <ChangeTable rows={rows} kept={new Set([2, 3])} />
      </div>
    ),
    "Narrow (under 560px)": (
      <div className="@container max-w-96">
        <Live initial={[1]} />
      </div>
    ),
  },
};
