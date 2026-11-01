import { useState } from "react";
import type { ReactNode } from "react";

import { Diff } from "@/component-elements/diff";
import { action, badge, eyebrow, frozen } from "@/copy/en";
import type { CardLifecycle } from "../card-lifecycle";
import { HarnessFrame } from "../card-shell.harness";
import { ResultCard } from "../result-card";

const live: CardLifecycle = {
  state: "live",
  frozenLine: undefined,
  press: () => {},
};

const diffLines = [
  { kind: "removed" as const, text: "Title: Build schedule and cache rollout" },
  { kind: "added" as const, text: "Title: Evening build retirement" },
  {
    kind: "removed" as const,
    text: "Motivation: evening build never finishes",
  },
  {
    kind: "added" as const,
    text: "Motivation: 7 of 9 evening runs hit the 6-hour limit",
  },
  { kind: "added" as const, text: "Status: Proposed. Approval is disputed." },
  {
    kind: "added" as const,
    text: "Still open: no timings from before the cache",
  },
];

function Saved({ open: start }: { open: boolean }) {
  const [open, setOpen] = useState(start);
  const id = start ? "r02-diff" : "r01-diff";
  return (
    <ResultCard
      kind="result"
      eyebrow={eyebrow.change}
      title="cache-proposal.md · 4 changes"
      badgeLabel={badge.done.saved}
      when="Oct 28, 09:41"
      undoMessage="Undo the 09:41 edit to cache-proposal.md"
      disclosure={{
        label: open ? action.hideChange : action.showChange,
        expanded: open,
        onToggle: () => setOpen(!open),
        controls: id,
      }}
      lifecycle={live}
    >
      <div id={id} hidden={!open}>
        <Diff lines={diffLines} />
      </div>
    </ResultCard>
  );
}

const undone = (
  <ResultCard
    kind="result"
    eyebrow={eyebrow.change}
    title="cache-proposal.md · 4 changes"
    badgeLabel={badge.done.undone}
    when="Oct 28, 09:44"
    who="undoes the 09:41 edit"
    lifecycle={live}
  />
);

const at = (w: "760" | "360", node: ReactNode) => (
  <div
    className={w === "760" ? "w-[760px] max-w-full" : "w-[360px] max-w-full"}
  >
    <HarnessFrame>{node}</HarnessFrame>
  </div>
);

export default {
  id: "P05",
  name: "Result and refusal",
  stories: {
    "R01 saved at 760px": at("760", <Saved open={false} />),
    "R01 saved at 360px": at("360", <Saved open={false} />),
    "R02 change open at 760px": at("760", <Saved open />),
    "R02 change open at 360px": at("360", <Saved open />),
    "R03 undone at 760px": at("760", undone),
    "R03 undone at 360px": at("360", undone),
    Refusal: (
      <HarnessFrame>
        <ResultCard
          kind="refusal"
          eyebrow="Undo"
          title="Undo: cache-proposal.md · 4 changes"
          badgeLabel={badge.refused.cantUndo}
          reason="cache-proposal.md changed after this edit (2 later edits)."
          nextStep={{
            label: action.showLaterEdits,
            message: "",
            frozenLine: frozen.notSaved,
            variant: "primary",
          }}
          lifecycle={live}
        />
      </HarnessFrame>
    ),
  },
};
