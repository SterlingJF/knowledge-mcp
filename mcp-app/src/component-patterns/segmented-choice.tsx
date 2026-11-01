// K11 Segmented choice: pick one of 2 or more answers. 2–3 sit side by side and stack when they don't fit; 4+ always stack.
// Places the K11 element's parts from data; the look is in component-elements/segmented-choice.tsx.
import { useLayoutEffect, useRef, useState } from "react";
import { flushSync } from "react-dom";

import {
  ToggleGroup,
  ToggleGroupItem,
} from "@/component-elements/segmented-choice";
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

/**
 * Stacks when the side-by-side row is wider than the space it has (the wrapper's max width).
 * The row's natural width is measured whenever it is side by side, and again when the options change,
 * so it only returns to a row when that width fits.
 */
function useStacked(always: boolean, key: string) {
  const wrap = useRef<HTMLDivElement>(null);
  const group = useRef<HTMLDivElement>(null);
  const natural = useRef(0);
  const [stacked, setStacked] = useState(false);

  // New options or labels: lay out as a row again and re-measure.
  useLayoutEffect(() => {
    natural.current = 0;
    setStacked(false);
  }, [key]);

  // While side by side, record the natural width and stack if it overflows.
  useLayoutEffect(() => {
    if (always || stacked || !wrap.current || !group.current) return;
    natural.current = group.current.scrollWidth;
    if (natural.current > wrap.current.clientWidth) setStacked(true);
  });

  // On resize, switch either way.
  useLayoutEffect(() => {
    if (always || typeof ResizeObserver === "undefined" || !wrap.current)
      return;
    const ro = new ResizeObserver(() => {
      const w = wrap.current;
      const g = group.current;
      if (!w || !g) return;
      // ResizeObserver runs after layout and before paint; committing synchronously means the
      // overflowing row is never painted.
      flushSync(() =>
        setStacked((was) => {
          if (!was) natural.current = g.scrollWidth;
          return natural.current > w.clientWidth;
        }),
      );
    });
    ro.observe(wrap.current);
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
  const key = options.map((o) => `${o.value}\u0000${o.label}`).join("\u0001");
  const { wrap, group, stacked } = useStacked(options.length > 3, key);

  return (
    // As wide as its row, never wider than its space (a caller may cap it with max-w); past that it stacks.
    <div
      ref={wrap}
      className={cn(
        "max-w-full min-w-0",
        stacked ? "w-full" : "w-max",
        className,
      )}
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
      >
        {options.map((option) => (
          <ToggleGroupItem
            key={option.value}
            value={option.value}
            role="radio"
            aria-checked={value === option.value}
            aria-pressed={undefined}
          >
            {option.label}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    </div>
  );
}
