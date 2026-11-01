import { badge } from "@/copy/en";
import { Badge } from "../badge";
import { FullViewButton } from "../full-view-button";

export default {
  id: "K13",
  name: "Full view button",
  stories: {
    "Beside the badge": (
      <span
        style={{
          display: "inline-flex",
          gap: "var(--km-gap-inline)",
          alignItems: "center",
        }}
      >
        <Badge tone="waiting">{badge.waiting.nothingSaved}</Badge>
        <FullViewButton onRequestFullView={() => {}} />
      </span>
    ),
    Focus: <FullViewButton autoFocus onRequestFullView={() => {}} />,
  },
};
