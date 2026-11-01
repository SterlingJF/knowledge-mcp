import { StaticCardHost, stubCardHost } from "@/bridge/static";
import { action, badge, frozen } from "@/copy/en";
import { lifecycleProps, useCardLifecycle } from "./card-lifecycle";
import { HarnessFrame, exampleMeta } from "./card-shell.harness";
import { CardShell } from "./card-shell";
import type { CardAction } from "./card-shell";

const actions: CardAction[] = [
  {
    label: action.save("C1–C4"),
    message: "",
    frozenLine: frozen.approved,
    variant: "primary",
  },
  { label: action.notNow, message: "", frozenLine: frozen.notSaved },
];
const shell = {
  eyebrow: "Proposed changes",
  title: "Focus the proposal on retiring the evening build",
  meta: exampleMeta,
  badge: { tone: "waiting" as const, label: badge.waiting.nothingSaved },
  actions,
};

const rememberedHost = stubCardHost({
  result: {
    schema: "gallery",
    instance: {
      subject: "gallery/remembered.md",
      created_at: "2026-10-28T09:41:00.000Z",
      seq: 1,
    },
  },
});

function Remembered() {
  const life = useCardLifecycle();
  return <CardShell {...shell} {...lifecycleProps(life)} />;
}

export default {
  id: "P06",
  name: "Card lifecycle",
  stories: {
    "Remembered: press, then reload the page": (
      <HarnessFrame>
        <StaticCardHost host={rememberedHost}>
          <Remembered />
        </StaticCardHost>
      </HarnessFrame>
    ),
    "1 · Drawn live": (
      <HarnessFrame>
        <CardShell {...shell} />
      </HarnessFrame>
    ),
    "2 · Pressed: approved": (
      <HarnessFrame>
        <CardShell
          {...shell}
          eyebrow="Change"
          badge={{ tone: "done", label: badge.done.approved }}
          state="frozen"
          frozenLine={frozen.approved}
        />
      </HarnessFrame>
    ),
    "2 · Pressed: not now": (
      <HarnessFrame>
        <CardShell
          {...shell}
          badge={{ tone: "neutral", label: badge.neutral.notSaved }}
          state="frozen"
          frozenLine={frozen.notSaved}
        />
      </HarnessFrame>
    ),
    "5 · Replaced": (
      <HarnessFrame>
        <CardShell {...shell} eyebrow="Change" state="replaced" />
      </HarnessFrame>
    ),
  },
};
