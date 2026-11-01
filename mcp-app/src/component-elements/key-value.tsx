// K08 Key–value list: the inline summary's data points, label left, value right; under 384px of card,
// each label sits above its value. Claude limits inline cards to 4–5 data points, so more than five rows is refused.
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
    <dl className={cn("flex flex-col gap-2", className)}>
      {rows.map((row, index) => (
        <div key={index} className="flex flex-col @sm:flex-row @sm:gap-4">
          <dt className="shrink-0 text-muted-foreground @sm:w-24">
            {row.label}
          </dt>
          <dd className="min-w-0">{row.value}</dd>
        </div>
      ))}
    </dl>
  );
}
