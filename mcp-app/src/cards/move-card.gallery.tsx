import { StaticCardHost, stubCardHost } from "@/bridge/static";
import type { CardLifecycle } from "@/component-patterns/card-lifecycle";
import { HarnessFrame } from "@/component-patterns/card-shell.harness";
import type { DocumentMoves } from "@/contracts/document-moves";
import { frozen } from "@/copy/en";
import { MoveView } from "./move-card";
import type { Answers, Pressed } from "./move-card";
import { m01, m05 } from "./move-card.fixture";

const lifecycle = (
  state: CardLifecycle["state"],
  frozenLine?: string,
): CardLifecycle => ({ state, frozenLine, press: () => {} });

function Story({
  plan = m01,
  mode = "inline",
  life = lifecycle("live"),
  answers = {},
  pressed,
}: {
  plan?: DocumentMoves;
  mode?: "inline" | "fullscreen";
  life?: CardLifecycle;
  answers?: Answers;
  pressed?: Pressed;
}) {
  return (
    <StaticCardHost host={stubCardHost({ displayMode: mode })}>
      <HarnessFrame>
        <MoveView
          plan={plan}
          displayMode={mode}
          answers={answers}
          onAnswer={() => {}}
          lifecycle={life}
          pressed={pressed}
        />
      </HarnessFrame>
    </StaticCardHost>
  );
}

export default {
  id: "C-Move",
  name: "Move card",
  stories: {
    "M01 Plan": <Story />,
    "M02 Full view": <Story mode="fullscreen" />,
    "M03 Approved": (
      <Story life={lifecycle("frozen", frozen.approved)} pressed="move" />
    ),
    "M05 Blockers": <Story plan={m05} />,
    "M05F Answer the blockers": <Story plan={m05} mode="fullscreen" />,
    "M05F Answered": (
      <Story
        plan={m05}
        mode="fullscreen"
        answers={{ b1: "accept", b2: "drop" }}
      />
    ),
    "M06 Not now": (
      <Story life={lifecycle("frozen", frozen.notMoved)} pressed="notNow" />
    ),
  },
};
