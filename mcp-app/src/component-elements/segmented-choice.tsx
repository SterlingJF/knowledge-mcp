import { ToggleGroup, ToggleGroupItem } from "@/component-core/toggle-group";
import { cn } from "@/lib/utils";

export type SegmentOption<V extends string> = { value: V; label: string };

export type SegmentedChoiceProps<V extends string> = {
  /** Two or three options, all visible. */
  options: readonly SegmentOption<V>[];
  /** null while undecided: no segment is selected. */
  value: V | null;
  onValueChange: (value: V) => void;
  "aria-label": string;
  className?: string;
};

/** Pick one of 2–3 options. Controlled; it never sends anything by itself. */
export function SegmentedChoice<V extends string>({
  options,
  value,
  onValueChange,
  className,
  ...rest
}: SegmentedChoiceProps<V>) {
  if (options.length < 2 || options.length > 3) {
    throw new Error("SegmentedChoice takes 2 or 3 options");
  }
  return (
    <ToggleGroup
      aria-label={rest["aria-label"]}
      spacing={0}
      value={value === null ? [] : [value]}
      onValueChange={(next) => {
        const picked = next[0] as V | undefined;
        if (picked !== undefined && picked !== value) onValueChange(picked);
      }}
      className={cn(
        "gap-0 overflow-hidden has-focus-visible:shadow-[var(--km-focus-ring)] rounded-[var(--border-radius-sm)] border-[length:var(--border-width-regular)] border-solid border-[var(--color-border-secondary)] whitespace-nowrap",
        className,
      )}
    >
      {options.map((option) => (
        <ToggleGroupItem
          key={option.value}
          value={option.value}
          className="h-auto min-w-0 rounded-none! px-[var(--km-space-5)] py-[var(--km-space-2)] text-[length:var(--font-text-xs-size)] font-[var(--font-weight-semibold)] text-[var(--color-text-tertiary)] hover:bg-[var(--color-background-secondary)] focus-visible:ring-0 focus-visible:shadow-[inset_var(--km-focus-ring)] focus-visible:relative focus-visible:z-10 pointer-coarse:min-h-[var(--km-target)] pointer-coarse:min-w-[var(--km-target)] [&+&]:border-l-[length:var(--border-width-regular)] [&+&]:border-solid [&+&]:border-[var(--color-border-secondary)] aria-pressed:bg-[var(--color-background-inverse)] aria-pressed:text-[var(--color-text-inverse)]"
        >
          {option.label}
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  );
}
