// P04 Decision rows: each row needs its own answer; decided rows show a badge in place of the choice.
import type { ReactNode } from "react";

import { Badge } from "@/component-elements/badge";
import { TickBox } from "@/component-elements/change-number";
import type { BadgeTone } from "@/component-elements/badge";
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
  /** This row's own answers: none is "Answer in chat", 1 is a K05 tick box, 2+ a segmented choice (4+ stack). Omit to use the table's `kind` preset. */
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

/** Which cell plays which part when the table stacks under 560px. Column indexes. */
/** Leave `title` unset when the cell bolds its own part (M05F bolds only the file name). */
export type NarrowLayout = { title?: number; detail?: number; hide?: number[] };
/** The conventions layout: type as the title, example as the detail, folder hidden. */
const conventionsNarrow: NarrowLayout = { title: 0, detail: 2, hide: [1] };

// The choice column sizes to its content, up to about two-thirds of the table; past that the label wraps or the options stack.
const cap = "w-max max-w-[65cqi] @max-[560px]:max-w-full";

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
      <span className="whitespace-nowrap text-xs leading-xs text-secondary">
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
        className={cap}
      />
    );
  }
  return (
    <SegmentedChoice<string>
      aria-label={row.name}
      // Capped so long options stack instead of widening the column.
      className={cn(cap, align === "end" && "ml-auto @max-[560px]:ml-0")}
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
  /** Under 560px: the title cell is semibold, the detail secondary mono, hidden cells go. Defaults to conventions. */
  narrow?: NarrowLayout;
  /** Where the choice sits in its column: "end" for conventions (P04), "start" for move blockers (M05F). */
  align?: "start" | "end";
  className?: string;
}) {
  const cellCount = rows[0]?.cells.length ?? headers.length;
  const part = (i: number) =>
    cn(
      i === narrow.title && "@max-[560px]:font-semibold",
      i === narrow.detail &&
        "@max-[560px]:font-(family-name:--font-mono) @max-[560px]:text-secondary",
      narrow.hide?.includes(i) && "@max-[560px]:hidden",
    );
  const cell = "py-km-gap-row pr-km-gap-group align-top";
  return (
    <table
      className={cn(
        "w-full border-collapse @max-[560px]:block @max-[560px]:[&_tbody]:block text-sm leading-sm text-foreground",
        className,
      )}
    >
      <thead className="@max-[560px]:sr-only">
        <tr className="border-b-hairline border-border text-left text-xs leading-xs font-semibold text-secondary">
          {headers.slice(0, cellCount).map((h, i) => (
            <th
              key={i}
              className={cn(cell, "pt-0 pb-km-gap-row font-[inherit]")}
            >
              {h}
            </th>
          ))}
          <th
            className={cn(
              cell,
              // The choice header never wraps; the column grows to it.
              "pt-0 pr-0 pb-km-gap-row font-[inherit] whitespace-nowrap",
              align === "end" && "text-right",
            )}
          >
            {headers[cellCount]}
          </th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr
            key={row.id}
            className="border-b-hairline border-border last:border-b-0 @max-[560px]:flex @max-[560px]:flex-col @max-[560px]:py-km-gap-row @max-[560px]:[&>td]:py-0 @max-[560px]:[&>td]:pr-0"
          >
            {row.cells.map((c, i) => (
              <td key={i} className={cn(cell, "break-words", part(i))}>
                {c}
              </td>
            ))}
            <td
              className={cn(
                cell,
                "w-px pr-0 @max-[560px]:mt-km-gap-row @max-[560px]:w-auto",
                align === "end" && "text-right @max-[560px]:text-left",
              )}
            >
              <Choice
                row={row}
                align={align}
                kind={kind}
                choices={choices}
                onChoiceChange={onChoiceChange}
              />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
