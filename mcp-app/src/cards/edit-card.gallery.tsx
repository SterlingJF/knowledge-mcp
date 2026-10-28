import { StaticCardHost, stubCardHost } from "@/bridge/static";
import type { CardLifecycle } from "@/component-patterns/card-lifecycle";
import { HarnessFrame } from "@/component-patterns/card-shell.harness";
import type { Edit } from "@/contracts/edit";
import { frozen } from "@/copy/en";
import { EditView } from "./edit-card";
import { d06, long, r01, r03 } from "./edit-card.fixture";

const lifecycle = (
  state: CardLifecycle["state"],
  frozenLine?: string,
): CardLifecycle => ({ state, frozenLine, press: () => {} });

function Story({
  edit = r01,
  life = lifecycle("live"),
  open,
}: {
  edit?: Edit;
  life?: CardLifecycle;
  open?: boolean;
}) {
  return (
    <StaticCardHost host={stubCardHost()}>
      <HarnessFrame>
        <EditView edit={edit} lifecycle={life} timeZone="UTC" open={open} />
      </HarnessFrame>
    </StaticCardHost>
  );
}

export default {
  id: "C-Result",
  name: "Edit result card",
  stories: {
    "R01 Saved, with Undo": <Story />,
    "R02 Change open": <Story open />,
    "R02 Long change open": <Story edit={long} open />,
    "R03 Undo requested": (
      <Story life={lifecycle("frozen", frozen.undoRequested)} />
    ),
    "R03 Undone": <Story edit={r03} />,
    "D06 Created and filed": <Story edit={d06} />,
    Replaced: <Story life={lifecycle("replaced")} />,
  },
};
