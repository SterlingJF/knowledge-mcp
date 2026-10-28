import { action, badge, frozen, label, line } from "@/copy/en";
import type { CardAction } from "./card-shell";
import type { CardLifecycle } from "./card-lifecycle";
import { FullViewLayout } from "./full-view";
import { SummaryCardView } from "./summary-card";

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
    variant: "primary",
  },
  { label: action.notNow, message: "", frozenLine: frozen.notSaved },
];
const head = {
  eyebrow: "Evidence review",
  title: "cache-proposal.md",
  badge: { tone: "waiting" as const, label: badge.waiting.needsOk },
  why: line.waitsBecause("cache-proposal.md"),
  actions,
  lifecycle: live,
};

export default {
  id: "P07",
  name: "Summary and full view",
  stories: {
    Summary: (
      <SummaryCardView
        {...head}
        onFullView={() => {}}
        rows={[
          { label: label.changes, value: "C1–C4 · 2 sections" },
          { label: label.evidence, value: "3 supported · 1 partly answered" },
          { label: label.leftOut, value: line.leftOut(2) },
        ]}
      />
    ),
    "Full view": (
      <FullViewLayout {...head}>
        <p>Every change, each with its sources.</p>
      </FullViewLayout>
    ),
  },
};
