import { StaticCardHost, stubCardHost } from "@/bridge/static";
import type { CardLifecycle } from "@/component-patterns/card-lifecycle";
import { HarnessFrame } from "@/component-patterns/card-shell.harness";
import type { Edit } from "@/contracts/edit";
import { frozen } from "@/copy/en";
import { EditView } from "./edit-card";
import { d06, r01 } from "./edit-card.fixture";

const lifecycle = (
  state: CardLifecycle["state"],
  frozenLine?: string,
): CardLifecycle => ({ state, frozenLine, press: () => {} });

function Story({
  edit = r01,
  life = lifecycle("live"),
}: {
  edit?: Edit;
  life?: CardLifecycle;
}) {
  return (
    <StaticCardHost host={stubCardHost()}>
      <HarnessFrame>
        <EditView edit={edit} lifecycle={life} timeZone="UTC" />
      </HarnessFrame>
    </StaticCardHost>
  );
}

export default {
  id: "C-Result",
  name: "Edit result card",
  stories: {
    "R01 Saved, with Undo": <Story />,
    "R03 Undo requested": (
      <Story life={lifecycle("frozen", frozen.undoRequested)} />
    ),
    "D06 Created and filed": <Story edit={d06} />,
    Replaced: <Story life={lifecycle("replaced")} />,
  },
};
