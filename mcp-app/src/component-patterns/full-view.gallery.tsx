import { StaticCardHost, stubCardHost } from "@/bridge/static";
import { action, badge, frozen, line } from "@/copy/en";
import type { CardAction } from "./card-shell";
import type { CardLifecycle } from "./card-lifecycle";
import { exampleMeta } from "./card-shell.harness";
import { FullView } from "./full-view";

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
    variant: "default",
  },
  { label: action.notNow, message: "", frozenLine: frozen.notSaved },
];

export default {
  id: "P07F",
  name: "Full view",
  stories: {
    "Full view frame (body from P02)": (
      <StaticCardHost host={stubCardHost({ displayMode: "fullscreen" })}>
        <FullView
          eyebrow="Proposed changes"
          title="Focus the proposal on retiring the evening build"
          badge={{ tone: "waiting", label: badge.waiting.nothingSaved }}
          meta={exampleMeta}
          why={line.waitsBecause("cache-proposal.md")}
          actions={actions}
          lifecycle={live}
        >
          <p>Every change, each with its sources.</p>
        </FullView>
      </StaticCardHost>
    ),
  },
};
