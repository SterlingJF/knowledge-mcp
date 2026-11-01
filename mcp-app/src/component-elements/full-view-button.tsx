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
      className="gap-km-2 border-input px-km-4 py-km-1 text-xs leading-xs"
    >
      {action.fullView}
    </Button>
  );
}
