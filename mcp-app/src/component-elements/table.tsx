// Table: core Table for the change, plan and decision tables. Cells wrap and sit at the top of their row;
// under 576px of card each row stacks into one column and the header row is kept for screen readers only.
// A row marked data-left-out reads muted.
import type { ComponentProps } from "react";

import {
  Table as CoreTable,
  TableBody as CoreTableBody,
  TableCell as CoreTableCell,
  TableHead as CoreTableHead,
  TableHeader as CoreTableHeader,
  TableRow as CoreTableRow,
} from "@/component-core/table";
import { cn } from "@/lib/utils";

export function Table({
  className,
  ...props
}: ComponentProps<typeof CoreTable>) {
  return (
    <CoreTable
      className={cn("table-fixed @max-xl:block", className)}
      {...props}
    />
  );
}

export function TableHeader({
  className,
  ...props
}: ComponentProps<typeof CoreTableHeader>) {
  return (
    <CoreTableHeader className={cn("@max-xl:sr-only", className)} {...props} />
  );
}

export function TableRow({
  className,
  ...props
}: ComponentProps<typeof CoreTableRow>) {
  return (
    <CoreTableRow
      className={cn(
        "hover:bg-transparent data-left-out:text-muted-foreground @max-xl:flex @max-xl:flex-col @max-xl:gap-2 @max-xl:py-3",
        className,
      )}
      {...props}
    />
  );
}

export function TableHead({
  className,
  ...props
}: ComponentProps<typeof CoreTableHead>) {
  return (
    <CoreTableHead
      className={cn(
        "h-auto pb-2 pl-0 text-xs text-muted-foreground",
        className,
      )}
      {...props}
    />
  );
}

/** The part a cell plays once its row stacks: the row's title, a quiet mono detail, or gone. */
export type StackedPart = "title" | "detail" | "hidden";

export function TableCell({
  stacked,
  className,
  ...props
}: ComponentProps<typeof CoreTableCell> & { stacked?: StackedPart }) {
  return (
    <CoreTableCell
      className={cn(
        "py-3 pl-0 align-top break-words whitespace-normal @max-xl:p-0",
        stacked === "title" && "@max-xl:font-semibold",
        stacked === "detail" &&
          "@max-xl:font-mono @max-xl:text-muted-foreground",
        stacked === "hidden" && "@max-xl:hidden",
        className,
      )}
      {...props}
    />
  );
}

export function TableBody(props: ComponentProps<typeof CoreTableBody>) {
  return <CoreTableBody {...props} />;
}
