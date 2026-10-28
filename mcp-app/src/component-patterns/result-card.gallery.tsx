import { action, badge, frozen } from "@/copy/en";
import type { CardLifecycle } from "./card-lifecycle";
import { HarnessFrame } from "./card-shell.harness";
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
      <HarnessFrame>
        <ResultCard
          kind="result"
          eyebrow="Saved"
          title="cache-proposal.md · 4 changes"
          badgeLabel={badge.done.saved}
          when="Oct 28, 09:41"
          undoMessage=""
          secondary={{
            label: action.showChange,
            message: "",
            frozenLine: frozen.approved,
          }}
          lifecycle={live}
        />
      </HarnessFrame>
    ),
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
