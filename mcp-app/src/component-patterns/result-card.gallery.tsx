import { badge, frozen } from "@/copy/en";
import type { CardLifecycle } from "./card-lifecycle";
import { ResultCard } from "./result-card";

const live: CardLifecycle = {
  state: "live",
  frozenLine: undefined,
  press: () => {},
};

export default {
  id: "P05",
  name: "Result and refusal",
  stories: {
    Result: (
      <ResultCard
        kind="result"
        eyebrow="Saved"
        title="cache-proposal.md · 4 changes"
        badgeLabel={badge.done.saved}
        what="Recorded"
        when="Oct 28, 09:41"
        who="approved by you"
        undoMessage=""
        secondary={{
          label: "Show the change",
          message: "",
          frozenLine: frozen.approved,
        }}
        lifecycle={live}
      />
    ),
    Refusal: (
      <ResultCard
        kind="refusal"
        eyebrow="Undo"
        title="Undo: cache-proposal.md · 4 changes"
        badgeLabel={badge.refused.cantUndo}
        reason="cache-proposal.md changed after this edit (2 later edits)."
        nextStep={{
          label: "Show the later edits",
          message: "",
          frozenLine: frozen.notSaved,
          variant: "primary",
        }}
        lifecycle={live}
      />
    ),
  },
};
