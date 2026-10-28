// K11 Segmented choice: pick one of 2 or more answers. 2–3 sit side by side and stack when they don't fit; 4+ always stack.
import { useLayoutEffect, useRef, useState } from "react";

import { ToggleGroup, ToggleGroupItem } from "@/component-core/toggle-group";
import { cn } from "@/lib/utils";

export type SegmentOption<V extends string> = { value: V; label: string };

export type SegmentedChoiceProps<V extends string> = {
  /** Two or more options, all visible. A single yes-or-no answer is a K05 tick box instead. */
  options: readonly SegmentOption<V>[];
  /** null while undecided: nothing is selected. */
  value: V | null;
  onValueChange: (value: V) => void;
  "aria-label": string;
  className?: string;
};

const groupClass =
  "gap-0 overflow-hidden has-focus-visible:shadow-(--km-focus-ring) rounded-(--border-radius-sm) border-(length:--border-width-regular) border-solid border-(--color-border-secondary)";

const itemClass =
  "h-auto min-w-0 rounded-none! px-(--km-space-5) py-(--km-space-2) text-(length:--font-text-xs-size) font-(--font-weight-semibold) text-(--color-text-tertiary) hover:bg-(--color-background-secondary) focus-visible:ring-0 focus-visible:shadow-[inset_0_0_0_2px_var(--color-ring-primary),inset_0_0_0_4px_var(--color-background-primary)] focus-visible:relative focus-visible:z-10 pointer-coarse:min-h-(--km-target) pointer-coarse:min-w-(--km-target) [&+&]:border-solid [&+&]:border-(--color-border-secondary) data-[state=on]:bg-(--color-background-inverse) aria-checked:bg-(--color-background-inverse) aria-checked:text-(--color-text-inverse)";

/**
 * Stacks when the side-by-side row is wider than the space it has.
 * The row's natural width is remembered while it is side by side, so it only returns when it fits again.
 */
function useStacked(always: boolean) {
  const wrap = useRef<HTMLDivElement>(null);
  const group = useRef<HTMLDivElement>(null);
  const natural = useRef(0);
  const [stacked, setStacked] = useState(always);

  useLayoutEffect(() => {
    if (always || typeof ResizeObserver === "undefined") return;
    const measure = () => {
      const w = wrap.current;
      const g = group.current;
      if (!w || !g) return;
      setStacked((was) => {
        if (!was) natural.current = g.scrollWidth;
        return natural.current > w.clientWidth;
      });
    };
    const ro = new ResizeObserver(measure);
    if (wrap.current) ro.observe(wrap.current);
    measure();
    return () => ro.disconnect();
  }, [always]);

  return { wrap, group, stacked: always || stacked };
}

export function SegmentedChoice<V extends string>({
  options,
  value,
  onValueChange,
  className,
  ...rest
}: SegmentedChoiceProps<V>) {
  if (options.length < 2)
    throw new Error("SegmentedChoice takes 2 or more options");
  const { wrap, group, stacked } = useStacked(options.length > 3);

  return (
    // inline-size containment: the row's width never props open its column; it stacks instead.
    <div
      ref={wrap}
      className={cn("w-full min-w-0 [contain:inline-size]", className)}
    >
      <ToggleGroup
        ref={group}
        role="radiogroup"
        aria-label={rest["aria-label"]}
        orientation={stacked ? "vertical" : "horizontal"}
        aria-orientation={stacked ? "vertical" : "horizontal"}
        spacing={0}
        data-layout={stacked ? "stacked" : "row"}
        value={value === null ? [] : [value]}
        onValueChange={(next) => {
          const picked = next[0] as V | undefined;
          if (picked !== undefined && picked !== value) onValueChange(picked);
        }}
        className={cn(
          groupClass,
          stacked
            ? "flex w-full flex-col items-stretch"
            : "w-max max-w-none whitespace-nowrap",
        )}
      >
        {options.map((option) => (
          <ToggleGroupItem
            key={option.value}
            value={option.value}
            role="radio"
            aria-checked={value === option.value}
            aria-pressed={undefined}
            className={cn(
              itemClass,
              stacked
                ? "w-full justify-start text-left whitespace-normal wrap-anywhere [&+&]:border-t-(length:--border-width-regular)"
                : "[&+&]:border-l-(length:--border-width-regular)",
            )}
          >
            {option.label}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    </div>
  );
}
