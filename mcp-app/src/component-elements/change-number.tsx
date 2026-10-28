// K05 Change number and tick box: names each change Cn and lets you keep it or leave it out before saving.
import { Checkbox } from "@/component-core/checkbox";
import { action } from "@/copy/en";
import { cn } from "@/lib/utils";

const rowClass =
  "inline-flex items-center gap-(--km-space-4) whitespace-nowrap font-(family-name:--font-mono) text-(length:--font-text-xs-size) leading-(--font-text-xs-line-height) font-(--font-weight-semibold) text-(--color-text-tertiary) pointer-coarse:min-h-(--km-target)";

const boxClass =
  "size-(--km-check) rounded-(--border-radius-xs) border-(length:--km-check-border) border-(--color-border-secondary) bg-transparent shadow-none after:hidden data-checked:border-transparent data-checked:bg-(--color-background-inverse) data-checked:text-(--color-text-inverse) data-indeterminate:border-transparent data-indeterminate:bg-(--color-background-inverse) data-indeterminate:text-(--color-text-inverse) data-indeterminate:[&_svg]:hidden data-indeterminate:before:h-(--km-space-1) data-indeterminate:before:w-(--km-space-4) data-indeterminate:before:rounded-(--km-space-1) data-indeterminate:before:bg-current data-indeterminate:before:content-[''] focus-visible:ring-(--color-ring-primary) [&_svg]:size-(--km-icon-sm)";

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
  const label = `C${n}`;
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
