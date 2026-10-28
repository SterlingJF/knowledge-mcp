import { Undo2 } from "lucide-react";

import { action } from "@/copy/en";
import { Button } from "./button";

export default {
  id: "K02",
  name: "Button",
  stories: {
    Primary: <Button variant="primary">{action.apply(3)}</Button>,
    Secondary: <Button variant="secondary">{action.notNow}</Button>,
    Ghost: <Button variant="ghost">{action.showWhy}</Button>,
    "With icon": <Button icon={<Undo2 />}>{action.undo}</Button>,
    Disabled: (
      <Button variant="primary" disabled>
        {action.apply(3)}
      </Button>
    ),
    Focus: (
      <Button variant="primary" autoFocus>
        {action.apply(3)}
      </Button>
    ),
  },
};
