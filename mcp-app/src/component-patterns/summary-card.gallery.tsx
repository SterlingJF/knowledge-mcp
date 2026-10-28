import { StaticCardHost, stubCardHost } from "@/bridge/static";
import { action, badge, frozen, label } from "@/copy/en";
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

export default {
  id: "P07",
  name: "Summary",
  stories: {
    Summary: (
      <StaticCardHost host={stubCardHost()}>
        <HarnessFrame>
          <SummaryCard
            eyebrow="Proposed changes"
            title="Focus the proposal on retiring the evening build"
            badge={{ tone: "waiting", label: badge.waiting.nothingSaved }}
            meta={exampleMeta}
            actions={actions}
            lifecycle={live}
            rows={[
              {
                label: label.changes,
                value:
                  "C1 Title · C2 Motivation · C3 Status · C4 Open question",
              },
              {
                label: label.evidence,
                value:
                  "1 supported · 1 partly answered · 1 conflicting · 1 suggested",
              },
              {
                label: label.needsYou,
                value: (
                  <>
                    <b>C3 Status</b> · slide 7 approved, notes disputed
                  </>
                ),
              },
              {
                label: label.leftOut,
                value: "vendor-quote.xlsx · release-calendar.md",
              },
            ]}
          />
        </HarnessFrame>
      </StaticCardHost>
    ),
  },
};
