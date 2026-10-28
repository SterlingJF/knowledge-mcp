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
    <div className={cn("@container mt-[var(--km-space-5)]", className)}>
      {/* Narrow: label above value. Wide: a label column. */}
      <dl className="m-0 grid grid-cols-1 gap-x-[var(--km-space-5)] gap-y-[var(--km-space-3)] @sm:grid-cols-[var(--km-label-col)_1fr]">
        {rows.map((row, index) => (
          <div key={index} className="contents">
            <dt className="text-[color:var(--color-text-tertiary)]">
              {row.label}
            </dt>
            <dd className="m-0">{row.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
