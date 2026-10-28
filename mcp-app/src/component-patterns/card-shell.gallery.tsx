import { action, badge, frozen, line } from "@/copy/en";
import { KeyValue } from "@/component-elements/key-value";
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
  eyebrow: "Evidence review",
  title: "cache-proposal.md",
  meta: "4 changes · 3 sources",
  badge: { tone: "waiting", label: badge.waiting.needsOk },
  why: line.waitsBecause("cache-proposal.md"),
  actions,
  onFullView: () => {},
  children: <KeyValue rows={[{ label: "Changes", value: "C1–C4" }]} />,
};

export default {
  id: "P01",
  name: "Card shell",
  stories: {
    Live: <CardShell {...base} />,
    Frozen: <CardShell {...base} state="frozen" frozenLine={frozen.approved} />,
    Replaced: <CardShell {...base} state="replaced" />,
    Flat: <CardShell {...base} onFullView={undefined} flat />,
  },
};
