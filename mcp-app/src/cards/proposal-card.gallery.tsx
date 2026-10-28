import { StaticCardHost, stubCardHost } from "@/bridge/static";
import type { CardLifecycle } from "@/component-patterns/card-lifecycle";
import { HarnessFrame } from "@/component-patterns/card-shell.harness";
import type { Proposal } from "@/contracts/proposal";
import { frozen } from "@/copy/en";
import { ProposalView } from "./proposal-card";
import type { Pressed } from "./proposal-card";
import { e02, newDocument } from "./proposal-card.fixture";

const lifecycle = (
  state: CardLifecycle["state"],
  frozenLine?: string,
): CardLifecycle => ({ state, frozenLine, press: () => {} });

function Story({
  proposal = e02,
  mode = "inline",
  life = lifecycle("live"),
  kept = new Set([1, 2, 3, 4]),
  pressed,
}: {
  pressed?: Pressed;
  proposal?: Proposal;
  mode?: "inline" | "fullscreen";
  life?: CardLifecycle;
  kept?: Set<number>;
}) {
  return (
    <StaticCardHost host={stubCardHost({ displayMode: mode })}>
      <HarnessFrame>
        <ProposalView
          proposal={proposal}
          displayMode={mode}
          kept={kept}
          onKeptChange={() => {}}
          lifecycle={life}
          pressed={pressed}
        />
      </HarnessFrame>
    </StaticCardHost>
  );
}

export default {
  id: "C-Proposal",
  name: "Proposal card",
  stories: {
    Inline: <Story />,
    "Full view": <Story mode="fullscreen" />,
    "Full view, C1 left out": (
      <Story mode="fullscreen" kept={new Set([2, 3, 4])} />
    ),
    "Frozen approved": (
      <Story life={lifecycle("frozen", frozen.approved)} pressed="save" />
    ),
    "Not saved": (
      <Story life={lifecycle("frozen", frozen.notSaved)} pressed="notNow" />
    ),
    Replaced: <Story life={lifecycle("replaced")} />,
    "New document (D05)": (
      <Story proposal={newDocument} kept={new Set([1, 2, 3])} />
    ),
    "New document full view (D05F)": (
      <Story
        proposal={newDocument}
        mode="fullscreen"
        kept={new Set([1, 2, 3])}
      />
    ),
  },
};
