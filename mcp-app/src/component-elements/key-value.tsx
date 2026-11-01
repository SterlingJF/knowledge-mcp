// K08 Key–value grid: the inline summary's data points, label left, value right.
// Claude limits inline cards to 4–5 data points, so more than five rows is refused.
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export const MAX_KEY_VALUE_ROWS = 5;

export type KeyValueRow = { label: ReactNode; value: ReactNode };

export function KeyValue({
  rows,
  className,
}: {
  rows: readonly KeyValueRow[];
  className?: string;
}) {
  if (rows.length > MAX_KEY_VALUE_ROWS) {
    throw new Error(
      `KeyValue shows at most ${MAX_KEY_VALUE_ROWS} rows; got ${rows.length}.`,
    );
  }
  return (
    <div className={cn("mt-km-gap-group", className)}>
      {/* Wide: a label column. Under 420px of the card: each label above its value. */}
      {/* Bracketed on purpose: the template mixes the label-column token with 1fr, which no token class names. */}
      <dl className="m-0 grid grid-cols-[var(--km-label-col)_1fr] gap-x-km-gap-group gap-y-km-gap-row @max-[420px]:grid-cols-1 @max-[420px]:gap-y-km-gap-tight">
        {rows.map((row, index) => (
          <div
            key={index}
            className="contents @max-[420px]:[&:not(:first-child)>dt]:mt-km-gap-tight"
          >
            <dt className="text-muted-foreground">{row.label}</dt>
            <dd className="m-0">{row.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
