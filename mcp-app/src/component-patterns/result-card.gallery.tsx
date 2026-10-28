import { action, badge, frozen } from "@/copy/en";
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
        eyebrow="Edit"
        title="cache-proposal.md"
        badgeLabel={badge.done.saved}
        what="4 changes"
        when="just now"
        who="you"
        undoMessage=""
        lifecycle={live}
      />
    ),
    Refusal: (
      <ResultCard
        kind="refusal"
        eyebrow="Edit"
        title="cache-proposal.md"
        badgeLabel={badge.refused.cantUndo}
        reason="The file changed after this edit, so undoing it would lose newer text. Nothing changed."
        nextStep={{
          label: action.prepareAgain,
          message: "",
          frozenLine: frozen.notSaved,
        }}
        lifecycle={live}
      />
    ),
  },
};
