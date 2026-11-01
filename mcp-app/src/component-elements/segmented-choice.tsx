// K11 Segmented choice, the look: core's toggle group restyled as one joined control, side by side or stacked.
// The orientation core already takes picks the row or stacked look. The data-driven choice with its stacking
// hook is the K11 pattern in component-patterns/segmented-choice.tsx.
import { createContext, useContext } from "react";
import type { ComponentProps } from "react";

import {
  ToggleGroup as CoreToggleGroup,
  ToggleGroupItem as CoreToggleGroupItem,
} from "@/component-core/toggle-group";
import { cn } from "@/lib/utils";

const groupClass =
  "gap-0 overflow-hidden has-focus-visible:shadow-(--km-focus-ring) rounded-(--border-radius-sm) border-(length:--border-width-regular) border-solid border-(--color-border-secondary)";

const itemClass =
  "h-auto min-w-0 rounded-none! px-(--km-space-5) py-(--km-space-2) text-(length:--font-text-xs-size) font-(--font-weight-semibold) text-(--color-text-tertiary) hover:bg-(--color-background-secondary) focus-visible:ring-0 focus-visible:shadow-[inset_0_0_0_2px_var(--color-ring-primary),inset_0_0_0_4px_var(--color-background-primary)] focus-visible:relative focus-visible:z-10 pointer-coarse:min-h-(--km-target) pointer-coarse:min-w-(--km-target) [&+&]:border-solid [&+&]:border-(--color-border-secondary) aria-checked:bg-(--color-background-inverse) aria-checked:text-(--color-text-inverse)";

const Stacked = createContext(false);

export function ToggleGroup({
  orientation = "horizontal",
  className,
  ...props
}: ComponentProps<typeof CoreToggleGroup>) {
  const stacked = orientation === "vertical";
  return (
    <Stacked.Provider value={stacked}>
      <CoreToggleGroup
        orientation={orientation}
        className={cn(
          groupClass,
          stacked
            ? "flex w-full flex-col items-stretch"
            : "w-max max-w-none whitespace-nowrap",
          className,
        )}
        {...props}
      />
    </Stacked.Provider>
  );
}

export function ToggleGroupItem({
  className,
  ...props
}: ComponentProps<typeof CoreToggleGroupItem>) {
  const stacked = useContext(Stacked);
  return (
    <CoreToggleGroupItem
      className={cn(
        itemClass,
        stacked
          ? "w-full justify-start text-left whitespace-normal wrap-anywhere [&+&]:border-t-(length:--border-width-regular)"
          : "[&+&]:border-l-(length:--border-width-regular)",
        className,
      )}
      {...props}
    />
  );
}
