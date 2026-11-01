// K05 Change number and tick box: core Checkbox in a core Label, so the whole label is the tap target.
// Names each change Cn and lets you keep it or leave it out before saving.
import { Checkbox } from "@/component-core/checkbox";
import { Label } from "@/component-core/label";
import { action, change } from "@/copy/en";
import { cn } from "@/lib/utils";

/** K05's tick box with any label: the whole label is the tap target. */
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
    <Label className={className}>
      <Checkbox checked={checked} onCheckedChange={(c) => onCheckedChange(c)} />
      {label}
    </Label>
  );
}

/** The Cn label. Without `onKeptChange` it is a frozen card's plain number. */
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
    return (
      <span className={cn("text-xs text-muted-foreground", className)}>
        {label}
      </span>
    );
  return (
    <TickBox
      label={label}
      checked={kept}
      onCheckedChange={onKeptChange}
      className={className}
    />
  );
}

/** The header box: ticks every row, or clears every row when all are ticked. */
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
  return (
    <TickBox
      label={action.all}
      checked={all}
      onCheckedChange={() => onChange(!all)}
      className={className}
    />
  );
}
