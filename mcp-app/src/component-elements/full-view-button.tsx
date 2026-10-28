import { Maximize2 } from "lucide-react";

import { Button } from "@/component-core/button";
import { action } from "@/copy/en";

export type FullViewButtonProps = { onRequestFullView: () => void };

/** Card-header control that opens the full view. It is chrome, not one of the card's actions. */
export function FullViewButton({ onRequestFullView }: FullViewButtonProps) {
  return (
    <Button
      variant="outline"
      data-km-chrome="full-view"
      onClick={onRequestFullView}
      className="h-auto gap-[var(--km-space-2)] rounded-[var(--border-radius-md)] border-[length:var(--border-width-regular)] border-solid border-[var(--color-border-secondary)] bg-transparent px-[var(--km-space-4)] py-[var(--km-space-1)] text-[length:var(--font-text-xs-size)] font-[var(--font-weight-semibold)] text-[var(--color-text-primary)] shadow-none focus-visible:ring-0 focus-visible:shadow-[0_0_0_2px_var(--color-background-primary),0_0_0_4px_var(--color-ring-primary)] pointer-coarse:min-h-[var(--km-target)] [&_svg:not([class*='size-'])]:size-[var(--km-icon)] dark:bg-transparent"
    >
      <Maximize2 aria-hidden="true" />
      {action.fullView}
    </Button>
  );
}
