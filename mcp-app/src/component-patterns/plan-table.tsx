// P08 Plan table: a read-only table of what a plan will do (M02 moves and links). Not built around Cn rows.
import { useState } from "react";
import type { CSSProperties, ReactNode } from "react";

import { line } from "@/copy/en";
import { cn } from "@/lib/utils";

export type PlanRow = { id: string; cells: ReactNode[] };

const xs =
  "text-(length:--font-text-xs-size) leading-(--font-text-xs-line-height)";
const label = cn(
  xs,
  "font-(--font-weight-semibold) text-(--color-text-secondary)",
);
// Wide: the table's own column fractions. Narrow (container under 560px): each row stacks, each cell under its header.
const rowClass =
  "grid grid-cols-(--plan-cols) items-start gap-x-(--km-space-5) gap-y-(--km-space-3) border-b-(length:--border-width-regular) border-(--color-border-tertiary) py-(--km-space-4) @max-[560px]:grid-cols-1";

/** A primary line with a secondary line under it. */
export function PlanLines({
  primary,
  secondary,
}: {
  primary: ReactNode;
  secondary?: ReactNode;
}) {
  return (
    <span className="flex min-w-0 flex-col">
      <span className="wrap-anywhere">{primary}</span>
      {secondary != null && (
        <span className={cn(xs, "wrap-anywhere text-(--color-text-tertiary)")}>
          {secondary}
        </span>
      )}
    </span>
  );
}

export function PlanTable({
  headers,
  columns,
  rows,
  limit,
  className,
}: {
  headers: string[];
  /** One fraction per column, e.g. [40, 60]. */
  columns: number[];
  rows: PlanRow[];
  /** Show only this many rows, then "+N more", which opens the rest in place. */
  limit?: number;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const hidden = limit != null && !open ? Math.max(rows.length - limit, 0) : 0;
  const shown = hidden > 0 ? rows.slice(0, limit) : rows;
  const style = {
    "--plan-cols": columns.map((f) => `minmax(0,${f}fr)`).join(" "),
  } as CSSProperties;

  return (
    <div
      role="table"
      style={style}
      className={cn(
        "@container text-(length:--font-text-sm-size) leading-(--font-text-sm-line-height) text-(--color-text-primary)",
        className,
      )}
    >
      <div
        role="row"
        className={cn(rowClass, "py-(--km-space-3) @max-[560px]:hidden")}
      >
        {headers.map((h) => (
          <span key={h} role="columnheader" className={label}>
            {h}
          </span>
        ))}
      </div>
      {shown.map((row) => (
        <div key={row.id} role="row" className={rowClass}>
          {row.cells.map((c, i) => (
            <span key={i} role="cell" className="min-w-0">
              <span
                aria-hidden
                data-stack-label
                className={cn(label, "hidden @max-[560px]:block")}
              >
                {headers[i]}
              </span>
              {c}
            </span>
          ))}
        </div>
      ))}
      {hidden > 0 && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className={cn(
            xs,
            "cursor-pointer rounded-(--border-radius-xs) border-0 bg-transparent px-0 py-(--km-space-4) text-(--color-text-tertiary) outline-none hover:text-(--color-text-primary) focus-visible:shadow-(--km-focus-ring) pointer-coarse:min-h-(--km-target)",
          )}
        >
          {line.andMore(hidden)}
        </button>
      )}
    </div>
  );
}
