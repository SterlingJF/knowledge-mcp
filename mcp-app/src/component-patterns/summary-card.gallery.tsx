import type { ReactNode } from "react";
import { StaticCardHost, stubCardHost } from "@/bridge/static";
import { action, badge, frozen, label, line } from "@/copy/en";
import type { CardAction } from "./card-shell";
import type { CardLifecycle } from "./card-lifecycle";
import { HarnessFrame, exampleMeta } from "./card-shell.harness";
import { SummaryCard } from "./summary-card";

const live: CardLifecycle = {
  state: "live",
  frozenLine: undefined,
  press: () => {},
};
const actions: CardAction[] = [
  {
    label: action.save("C1–C4"),
    message: "",
    frozenLine: frozen.approved,
    variant: "primary",
  },
  { label: action.notNow, message: "", frozenLine: frozen.notSaved },
];

const joined = (...parts: string[]) => parts.join(line.summaryJoin);

const card = (
  <SummaryCard
    why={line.waitsBecause("cache-proposal.md")}
    eyebrow="Proposed changes"
    title="Focus the proposal on retiring the evening build"
    badge={{ tone: "waiting", label: badge.waiting.nothingSaved }}
    meta={exampleMeta}
    actions={actions}
    lifecycle={live}
    rows={[
      {
        label: label.changes,
        value: joined(
          "C1 Title",
          "C2 Motivation",
          "C3 Status",
          "C4 Open question",
        ),
      },
      {
        label: label.evidence,
        value: joined(
          line.counted(1, "supported"),
          line.counted(1, "partly answered"),
          line.counted(1, "conflicting"),
          line.counted(1, "suggested"),
        ),
      },
      {
        label: label.needsYou,
        value: (
          <>
            <b>C3 Status</b>
            {line.summaryJoin}slide 7 approved, notes disputed
          </>
        ),
      },
      {
        label: label.leftOut,
        value: joined("vendor-quote.xlsx", "release-calendar.md"),
      },
    ]}
  />
);

const framed = (body: ReactNode) => (
  <StaticCardHost host={stubCardHost()}>
    <HarnessFrame>{body}</HarnessFrame>
  </StaticCardHost>
);

export default {
  id: "P07",
  name: "Summary",
  stories: {
    Summary: framed(card),
    // The narrowest phone: the header stacks and each label sits above its value.
    "Summary at 360px": framed(<div className="w-90">{card}</div>),
  },
};
