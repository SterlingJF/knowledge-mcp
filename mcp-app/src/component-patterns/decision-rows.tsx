// P04 Decision rows: each row needs its own answer; decided rows show a badge in place of the choice.
import type { ReactNode } from "react";

import { Badge } from "@/component-elements/badge";
import type { BadgeTone } from "@/component-elements/badge";
import { TickBox } from "@/component-patterns/change-number";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/component-elements/table";
import { SegmentedChoice } from "@/component-patterns/segmented-choice";
import type { SegmentOption } from "@/component-patterns/segmented-choice";
import { decision } from "@/copy/en";
import { cn } from "@/lib/utils";

export type DecisionKind = "acceptDrop" | "applyKeepRefused";
export type DecisionValue = "accept" | "drop" | "apply" | "keepRefused";

/** The two preset option sets; a row may bring its own instead. */
export const decisionOptions: Record<
  DecisionKind,
  readonly SegmentOption<DecisionValue>[]
> = {
  acceptDrop: [
    { value: "accept", label: decision.accept },
    { value: "drop", label: decision.drop },
  ],
  applyKeepRefused: [
    { value: "apply", label: decision.apply },
    { value: "keepRefused", label: decision.keepRefused },
  ],
};

export type DecisionRow = {
  id: string;
  /** Names the row for its choice's accessible label. */
  name: string;
  cells: ReactNode[];
  /** This row's own answers: none is "Answer in chat", 1 is a K05 tick box, 2+ a choice, one option per line. Omit to use the table's `kind` preset. */
  options?: readonly SegmentOption<string>[];
  /** This row's answer; overrides `choices[id]`. */
  value?: string | null;
  /** Set once the decision is recorded: the badge replaces the choice. Label comes from copy. */
  decided?: { tone: BadgeTone; label: string };
};

/**
 * How many rows will be saved: the count for the card's primary button.
 * Counts only the preset answers "accept" and "apply". A per-row option (a move blocker's answer)
 * never counts: answering a blocker is not accepting a row.
 */
export function countAccepted(
  choices: Record<string, string | null | undefined>,
): number {
  return Object.values(choices).filter((v) => v === "accept" || v === "apply")
    .length;
}

/** Which cell plays which part when the table stacks under 576px. Column indexes. */
/** Leave `title` unset when the cell bolds its own part (M05F bolds only the file name). */
export type NarrowLayout = { title?: number; detail?: number; hide?: number[] };
/** The conventions layout: type as the title, example as the detail, folder hidden. */
const conventionsNarrow: NarrowLayout = { title: 0, detail: 2, hide: [1] };

function Choice({
  row,
  kind,
  align,
  choices,
  onChoiceChange,
}: {
  row: DecisionRow;
  align: "start" | "end";
  kind: DecisionKind;
  choices: Record<string, string | null | undefined>;
  onChoiceChange: (id: string, value: string | null) => void;
}) {
  if (row.decided)
    return <Badge tone={row.decided.tone}>{row.decided.label}</Badge>;
  const options = row.options ?? decisionOptions[kind];
  const value = row.value !== undefined ? row.value : (choices[row.id] ?? null);
  // No answer the card can offer: it is answered in chat, and the row stays unanswered.
  if (options.length === 0)
    return (
      <span className="text-xs whitespace-nowrap text-muted-foreground">
        {decision.answerInChat}
      </span>
    );
  // One answer: a K05 tick box. Ticking sets it; clearing goes back to undecided.
  if (options.length === 1) {
    const only = options[0];
    return (
      <TickBox
        label={only.label}
        checked={value === only.value}
        onCheckedChange={(on) => onChoiceChange(row.id, on ? only.value : null)}
      />
    );
  }
  return (
    <SegmentedChoice<string>
      aria-label={row.name}
      className={cn(align === "end" && "justify-end @max-xl:justify-start")}
      options={options}
      value={value}
      onValueChange={(v) => onChoiceChange(row.id, v)}
    />
  );
}

export function DecisionRows({
  headers,
  rows,
  kind = "acceptDrop",
  choices = {},
  onChoiceChange,
  narrow = conventionsNarrow,
  align = "end",
  className,
}: {
  /** One per cell; one more labels the choice column (M05F "Your choice"). */
  headers: ReactNode[];
  rows: DecisionRow[];
  kind?: DecisionKind;
  /** Owned by the parent; null or absent means undecided. */
  choices?: Record<string, string | null | undefined>;
  /** null only when a single-option row's tick box is cleared. */
  onChoiceChange: (id: string, value: string | null) => void;
  /** Under 576px: the title cell is semibold, the detail secondary mono, hidden cells go. Defaults to conventions. */
  narrow?: NarrowLayout;
  /** Where the choice sits in its column: "end" for conventions (P04), "start" for move blockers (M05F). */
  align?: "start" | "end";
  className?: string;
}) {
  const cellCount = rows[0]?.cells.length ?? headers.length;
  return (
    <Table className={className}>
      <TableHeader>
        <TableRow>
          {headers.slice(0, cellCount).map((h, i) => (
            <TableHead key={i}>{h}</TableHead>
          ))}
          <TableHead className={cn(align === "end" && "text-right")}>
            {headers[cellCount]}
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row.id}>
            {row.cells.map((c, i) => (
              <TableCell
                key={i}
                stacked={
                  i === narrow.title
                    ? "title"
                    : i === narrow.detail
                      ? "detail"
                      : narrow.hide?.includes(i)
                        ? "hidden"
                        : undefined
                }
              >
                {c}
              </TableCell>
            ))}
            <TableCell
              className={cn(align === "end" && "text-right @max-xl:text-left")}
            >
              <Choice
                row={row}
                align={align}
                kind={kind}
                choices={choices}
                onChoiceChange={onChoiceChange}
              />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
