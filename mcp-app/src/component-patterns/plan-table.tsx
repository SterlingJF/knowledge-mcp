// P08 Plan table: a read-only table of what a plan will do (M02 moves and links). Not built around Cn rows.
// Narrow, each cell shows its header above it.
import { useState } from "react";
import type { ReactNode } from "react";

import { Button } from "@/component-core/button";
import { NoBreakName } from "@/component-elements/chips";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/component-elements/table";
import { line } from "@/copy/en";

export type PlanRow = { id: string; cells: ReactNode[] };

const named = (text: ReactNode) =>
  typeof text === "string" ? <NoBreakName>{text}</NoBreakName> : text;

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
      <span>{named(primary)}</span>
      {secondary != null && (
        <span className="text-xs text-muted-foreground">
          {named(secondary)}
        </span>
      )}
    </span>
  );
}

export function PlanTable({
  headers,
  rows,
  limit,
  className,
}: {
  headers: string[];
  rows: PlanRow[];
  /** Show only this many rows, then "+N more", which opens the rest in place. */
  limit?: number;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const hidden = limit != null && !open ? Math.max(rows.length - limit, 0) : 0;
  const shown = hidden > 0 ? rows.slice(0, limit) : rows;

  return (
    <div className={className}>
      <Table>
        <TableHeader>
          <TableRow>
            {headers.map((h) => (
              <TableHead key={h}>{h}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {shown.map((row) => (
            <TableRow key={row.id}>
              {row.cells.map((c, i) => (
                <TableCell key={i}>
                  <span
                    aria-hidden
                    data-stack-label
                    className="hidden text-xs text-muted-foreground @max-xl:block"
                  >
                    {headers[i]}
                  </span>
                  {c}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {hidden > 0 && (
        <Button variant="ghost" size="sm" onClick={() => setOpen(true)}>
          {line.andMore(hidden)}
        </Button>
      )}
    </div>
  );
}
