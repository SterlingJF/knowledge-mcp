import { StaticCardHost, stubCardHost } from "@/bridge/static";
import { action, badge, frozen, label, line } from "@/copy/en";
import type { CardAction } from "./card-shell";
import type { CardLifecycle } from "./card-lifecycle";
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
        <SummaryCard
          eyebrow="Proposed changes"
          title="Focus the proposal on retiring the evening build"
          badge={{ tone: "waiting", label: badge.waiting.nothingSaved }}
          why={line.waitsBecause("cache-proposal.md")}
          actions={actions}
          lifecycle={live}
          rows={[
            {
              label: label.changes,
              value: "C1–C4: title, motivation, status, open question",
            },
            {
              label: label.evidence,
              value:
                "1 supported · 1 partly answered · 1 conflicting · 1 suggested",
            },
            { label: label.leftOut, value: line.leftOut(2) },
          ]}
        />
      </StaticCardHost>
    ),
  },
};
