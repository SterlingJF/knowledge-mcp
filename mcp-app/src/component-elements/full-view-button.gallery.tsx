import { badge } from "@/copy/en";
import { Badge } from "./badge";
import { FullViewButton } from "./full-view-button";

export default {
  id: "K13",
  name: "Full view button",
  stories: {
    "Beside the badge": (
      <span className="inline-flex items-center gap-km-gap-inline">
        <Badge tone="waiting">{badge.waiting.nothingSaved}</Badge>
        <FullViewButton onRequestFullView={() => {}} />
      </span>
    ),
    Focus: <FullViewButton autoFocus onRequestFullView={() => {}} />,
  },
};
