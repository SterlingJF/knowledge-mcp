import { badge } from "@/copy/en";
import { Badge } from "./badge";

export default {
  id: "K01",
  name: "Badge",
  stories: {
    Waiting: <Badge tone="waiting">{badge.waiting.needsOk}</Badge>,
    Done: <Badge tone="done">{badge.done.saved}</Badge>,
    Refused: <Badge tone="refused">{badge.refused.cantUndo}</Badge>,
    Working: <Badge tone="working">{badge.working.checking}</Badge>,
    Neutral: <Badge tone="neutral">{badge.neutral.notSaved}</Badge>,
  },
};
