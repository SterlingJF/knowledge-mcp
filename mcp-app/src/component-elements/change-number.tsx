// K05 Change number and tick box: names each change Cn and lets you keep it or leave it out before saving.
import { Checkbox } from "@/component-core/checkbox";
import { action, change } from "@/copy/en";
import { cn } from "@/lib/utils";

const rowClass =
  "inline-flex items-center gap-(--km-gap-inline) whitespace-nowrap font-(family-name:--font-mono) text-(length:--font-text-xs-size) leading-(--font-text-xs-line-height) font-(--font-weight-semibold) text-(--color-text-tertiary) relative pointer-coarse:before:absolute pointer-coarse:before:top-1/2 pointer-coarse:before:left-0 pointer-coarse:before:h-(--km-target) pointer-coarse:before:w-full pointer-coarse:before:min-w-(--km-target) pointer-coarse:before:-translate-y-1/2 pointer-coarse:before:content-['']";

const boxClass =
  "size-(--km-check) rounded-(--border-radius-xs) border-(length:--km-check-border) border-(--color-text-tertiary) bg-transparent shadow-none after:hidden data-checked:border-transparent data-checked:bg-(--color-background-inverse) data-checked:text-(--color-text-inverse) data-indeterminate:border-transparent data-indeterminate:bg-(--color-background-inverse) data-indeterminate:text-(--color-text-inverse) data-indeterminate:[&_svg]:hidden data-indeterminate:before:h-(--km-space-1) data-indeterminate:before:w-(--km-space-4) data-indeterminate:before:rounded-(--km-space-1) data-indeterminate:before:bg-current data-indeterminate:before:content-[''] focus-visible:border-transparent focus-visible:ring-0 focus-visible:shadow-(--km-focus-ring) [&_svg]:size-(--km-icon-sm)";

/**
 * The Cn label. Without `onKeptChange` it is a frozen card's plain number.
 * With it, the whole row is a label wrapping a tick box, so the row is the tap target.
 */
export function ChangeNumber({
  n,
  kept = true,
  onKeptChange,
  className,
}: {
  n: number;
  kept?: boolean;
  onKeptChange?: (kept: boolean) => void;
  className?: string;
}) {
  const label = change.number(n);
  if (!onKeptChange)
    return <span className={cn(rowClass, className)}>{label}</span>;
  return (
    <label className={cn(rowClass, "cursor-pointer", className)}>
      <Checkbox
        className={boxClass}
        checked={kept}
        onCheckedChange={(checked) => onKeptChange(checked)}
      />
      {label}
    </label>
  );
}

/** K05's tick box with any label, for a single yes-or-no answer (a one-option decision row). */
export function TickBox({
  label,
  checked,
  onCheckedChange,
  className,
}: {
  label: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  className?: string;
}) {
  return (
    <label
      className={cn(
        rowClass,
        // A long label wraps; the box stays on the first line.
        "cursor-pointer items-start whitespace-normal font-(family-name:--font-sans) text-(--color-text-primary)",
        className,
      )}
    >
      <Checkbox
        className={cn(boxClass, "mt-[calc((1lh-var(--km-check))/2)] shrink-0")}
        checked={checked}
        onCheckedChange={(c) => onCheckedChange(c)}
      />
      <span className="min-w-0">{label}</span>
    </label>
  );
}

/** The header box: ticks every row, clears every row, or shows a dash when some are left out. */
export function SelectAll({
  keptCount,
  total,
  onChange,
  className,
}: {
  keptCount: number;
  total: number;
  onChange: (keepAll: boolean) => void;
  className?: string;
}) {
  const all = keptCount === total;
  const mixed = keptCount > 0 && !all;
  return (
    <label className={cn(rowClass, "cursor-pointer", className)}>
      <Checkbox
        className={boxClass}
        checked={all}
        indeterminate={mixed}
        onCheckedChange={() => onChange(!all)}
      />
      {action.all}
    </label>
  );
}
