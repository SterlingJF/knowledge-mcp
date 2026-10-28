import { action, badge, frozen, line } from "@/copy/en";
import { CardShell } from "./card-shell";
import type { CardAction, CardShellProps } from "./card-shell";

const actions: CardAction[] = [
  {
    label: action.save("C1–C4"),
    message: "",
    frozenLine: frozen.approved,
    variant: "primary",
  },
  { label: action.notNow, message: "", frozenLine: frozen.notSaved },
];

const base: CardShellProps = {
  eyebrow: "Proposed changes",
  title: "Focus the proposal on retiring the evening build",
  meta: "cache-proposal.md · Design proposal · for maintainers deciding whether to accept it",
  badge: { tone: "waiting", label: badge.waiting.nothingSaved },
  why: line.waitsBecause("cache-proposal.md"),
  actions,
};

export default {
  id: "P01",
  name: "Card shell",
  stories: {
    Live: <CardShell {...base} />,
    Frozen: (
      <CardShell
        {...base}
        eyebrow="Change"
        badge={{ tone: "done", label: badge.done.approved }}
        state="frozen"
        frozenLine={frozen.approved}
      />
    ),
    Replaced: <CardShell {...base} eyebrow="Change" state="replaced" />,
    Flat: <CardShell {...base} flat />,
  },
};
