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
  eyebrow: "Evidence review",
  title: "cache-proposal.md",
  badge: { tone: "waiting" as const, label: badge.waiting.needsOk },
  actions,
};

export default {
  id: "P06",
  name: "Card lifecycle",
  stories: {
    Live: <CardShell {...shell} />,
    "Frozen: approved": (
      <CardShell {...shell} state="frozen" frozenLine={frozen.approved} />
    ),
    "Frozen: not now": (
      <CardShell {...shell} state="frozen" frozenLine={frozen.notSaved} />
    ),
    Replaced: <CardShell {...shell} state="replaced" />,
  },
};
