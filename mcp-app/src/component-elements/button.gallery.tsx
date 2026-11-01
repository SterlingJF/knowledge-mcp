import { Undo2 } from "lucide-react";
import type { ReactNode } from "react";

import { action, change } from "@/copy/en";
import { Button, type ButtonVariant } from "./button";

const kinds: { variant: ButtonVariant; label: string; icon?: ReactNode }[] = [
  { variant: "primary", label: action.save(change.range(1, 4)) },
  { variant: "secondary", label: action.undo, icon: <Undo2 /> },
  { variant: "ghost", label: action.notNow },
];

const row = (state: "default" | "focus" | "disabled") => (
  <span className="inline-flex gap-km-gap-inline">
    {kinds.map(({ variant, label, icon }) => (
      <Button
        key={variant}
        variant={variant}
        icon={icon}
        disabled={state === "disabled"}
        autoFocus={state === "focus" && variant === "primary"}
      >
        {label}
      </Button>
    ))}
  </span>
);

export default {
  id: "K02",
  name: "Button",
  stories: {
    Default: row("default"),
    "Focus (Tab to move)": row("focus"),
    Disabled: row("disabled"),
  },
};
