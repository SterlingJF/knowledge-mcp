import { PathChip } from "@/component-elements/chips";

import { PlanLines, PlanTable } from "./plan-table";

const mono = (t: string) => (
  <span className="font-mono wrap-anywhere">{t}</span>
);

const file = (name: string, from: string) => (
  <PlanLines
    primary={<b className="font-semibold">{name}</b>}
    secondary={from}
  />
);

const moves = (
  <PlanTable
    headers={["File", "Goes to"]}
    rows={[
      {
        id: "1",
        cells: [
          file("build-review-notes.md", "Inbox"),
          <PlanLines
            key="to"
            primary="Meetings/"
            secondary="as 2026-10-27 build review.md"
          />,
        ],
      },
      {
        id: "2",
        cells: [
          file("retire-evening.md", "Inbox"),
          <PlanLines
            key="to"
            primary="Decisions/"
            secondary="as 2026-10-28 retire evening build.md"
          />,
        ],
      },
      {
        id: "3",
        cells: [
          file("timings-notes.md", "Inbox"),
          <PlanLines key="to" primary="Proposals/" />,
        ],
      },
    ]}
  />
);

const linkRows = [
  [
    "decisions-index.md:12",
    "[[retire-evening]]",
    "[[2026-10-28 retire evening build]]",
  ],
  ["cache-proposal.md:40", "[[timings-notes]]", "[[Proposals/timings-notes]]"],
  [
    "weekly-2026-43.md:7",
    "[[build-review-notes]]",
    "[[2026-10-27 build review]]",
  ],
  [
    "weekly-2026-44.md:3",
    "[[retire-evening]]",
    "[[2026-10-28 retire evening build]]",
  ],
  ["roadmap.md:21", "[[timings-notes]]", "[[Proposals/timings-notes]]"],
].map(([note, now, after], i) => ({
  id: String(i),
  cells: [<PathChip key="note" path={note} />, mono(now), mono(after)],
}));

const links = (
  <PlanTable
    headers={["Note", "Link now", "After the move"]}
    rows={linkRows}
    limit={3}
  />
);

export default {
  id: "P08",
  name: "Plan table",
  stories: {
    "Moves at 727px": (
      <div className="@container w-181.75 max-w-full">{moves}</div>
    ),
    "Moves at 360px": <div className="@container w-90 max-w-full">{moves}</div>,
    "Links at 727px": (
      <div className="@container w-181.75 max-w-full">{links}</div>
    ),
    "Links at 360px": <div className="@container w-90 max-w-full">{links}</div>,
  },
};
