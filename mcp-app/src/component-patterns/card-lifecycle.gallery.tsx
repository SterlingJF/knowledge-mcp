import { action, badge, frozen } from "@/copy/en";
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
  badge: { tone: "waiting" as const, label: badge.waiting.nothingSaved },
  actions,
};

export default {
  id: "P06",
  name: "Card lifecycle",
  stories: {
    "1 · Drawn live": <CardShell {...shell} />,
    "2 · Pressed: approved": (
      <CardShell
        {...shell}
        eyebrow="Change"
        badge={{ tone: "done", label: badge.done.approved }}
        state="frozen"
        frozenLine={frozen.approved}
      />
    ),
    "2 · Pressed: not now": (
      <CardShell
        {...shell}
        badge={{ tone: "neutral", label: badge.neutral.notSaved }}
        state="frozen"
        frozenLine={frozen.notSaved}
      />
    ),
    "5 · Replaced": <CardShell {...shell} eyebrow="Change" state="replaced" />,
  },
};
