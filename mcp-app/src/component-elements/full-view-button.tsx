import { Maximize2 } from "lucide-react";

import { action } from "@/copy/en";
import { Button } from "./button";

export type FullViewButtonProps = {
  onRequestFullView: () => void;
  autoFocus?: boolean;
};

/** Card-header control that opens the full view. It is chrome, not one of the card's actions. */
export function FullViewButton({
  onRequestFullView,
  autoFocus,
}: FullViewButtonProps) {
  return (
    <Button
      variant="ghost"
      data-km-chrome="full-view"
      autoFocus={autoFocus}
      onClick={onRequestFullView}
      icon={<Maximize2 aria-hidden="true" />}
      className="gap-[var(--km-space-2)] border-[var(--color-border-secondary)] px-[var(--km-space-4)] py-[var(--km-space-1)] text-[length:var(--font-text-xs-size)] leading-[var(--font-text-xs-line-height)]"
    >
      {action.fullView}
    </Button>
  );
}
