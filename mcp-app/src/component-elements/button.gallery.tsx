import { ChevronDown, Maximize2, Undo2 } from "lucide-react";

import { Button } from "@/component-core/button";
import { action, change } from "@/copy/en";

const row = (state: "default" | "focus" | "disabled") => (
  <span className="inline-flex flex-wrap gap-2">
    <Button autoFocus={state === "focus"} disabled={state === "disabled"}>
      {action.save(change.range(1, 4))}
    </Button>
    <Button variant="outline" disabled={state === "disabled"}>
      <Undo2 aria-hidden="true" data-icon="inline-start" />
      {action.undo}
    </Button>
    <Button variant="ghost" disabled={state === "disabled"}>
      {action.notNow}
    </Button>
  </span>
);

// Core Button as the cards use it: the one filled action, Undo outlined, the decline ghost;
// Full view (K13) outlined small in the header; Show the change (K15) ghost with a chevron.
export default {
  id: "K02",
  name: "Button",
  stories: {
    Default: row("default"),
    "Focus (Tab to move)": row("focus"),
    Disabled: row("disabled"),
    "Full view (K13)": (
      <Button variant="outline" size="xs">
        <Maximize2 aria-hidden="true" data-icon="inline-start" />
        {action.fullView}
      </Button>
    ),
    "Show the change (K15)": (
      <Button variant="ghost">
        {action.showChange}
        <ChevronDown aria-hidden="true" data-icon="inline-end" />
      </Button>
    ),
  },
};
