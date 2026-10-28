// P04 Decision rows: each row needs its own answer; decided rows show a badge in place of the choice.
import type { ReactNode } from "react";

import { Badge } from "@/component-elements/badge";
import { TickBox } from "@/component-elements/change-number";
import type { BadgeTone } from "@/component-elements/badge";
import { SegmentedChoice } from "@/component-elements/segmented-choice";
import type { SegmentOption } from "@/component-elements/segmented-choice";
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
  /** This row's own answers: 1 is a K05 tick box, 2+ a segmented choice (4+ stack). Omit to use the table's `kind` preset. */
  options?: readonly SegmentOption<string>[];
  /** This row's answer; overrides `choices[id]`. */
  value?: string | null;
  /** Set once the decision is recorded: the badge replaces the choice. Label comes from copy. */
  decided?: { tone: BadgeTone; label: string };
};

/** How many rows will be saved: the count for the card's primary button. */
export function countAccepted(
  choices: Record<string, string | null | undefined>,
): number {
  return Object.values(choices).filter((v) => v === "accept" || v === "apply")
    .length;
}

function Choice({
  row,
  kind,
  choices,
  onChoiceChange,
}: {
  row: DecisionRow;
  kind: DecisionKind;
  choices: Record<string, string | null | undefined>;
  onChoiceChange: (id: string, value: string | null) => void;
}) {
  if (row.decided)
    return <Badge tone={row.decided.tone}>{row.decided.label}</Badge>;
  const options = row.options ?? decisionOptions[kind];
  const value = row.value !== undefined ? row.value : (choices[row.id] ?? null);
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
      className="[&>[role=radiogroup]]:ml-auto @max-[560px]:[&>[role=radiogroup]]:ml-0"
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
  className,
}: {
  headers: ReactNode[];
  rows: DecisionRow[];
  kind?: DecisionKind;
  /** Owned by the parent; null or absent means undecided. */
  choices?: Record<string, string | null | undefined>;
  /** null only when a single-option row's tick box is cleared. */
  onChoiceChange: (id: string, value: string | null) => void;
  className?: string;
}) {
  const cell = "py-(--km-gap-row) pr-(--km-gap-group) align-top";
  return (
    <table
      className={cn(
        "w-full border-collapse @max-[560px]:block @max-[560px]:[&_tbody]:block text-(length:--font-text-sm-size) leading-(--font-text-sm-line-height) text-(--color-text-primary)",
        className,
      )}
    >
      <thead className="@max-[560px]:sr-only">
        <tr className="border-b-(length:--border-width-regular) border-(--color-border-tertiary) text-left text-(length:--font-text-xs-size) leading-(--font-text-xs-line-height) font-(--font-weight-semibold) text-(--color-text-secondary)">
          {headers.map((h, i) => (
            <th
              key={i}
              className={cn(cell, "pt-0 pb-(--km-gap-row) font-[inherit]")}
            >
              {h}
            </th>
          ))}
          <th className={cn(cell, "pr-0")} />
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr
            key={row.id}
            className="border-b-(length:--border-width-regular) border-(--color-border-tertiary) last:border-b-0 @max-[560px]:flex @max-[560px]:flex-col @max-[560px]:py-(--km-gap-row) @max-[560px]:[&>td]:py-0 @max-[560px]:[&>td]:pr-0"
          >
            {row.cells.map((c, i) => (
              <td key={i} className={cn(cell, "wrap-anywhere")}>
                {c}
              </td>
            ))}
            <td
              className={cn(
                cell,
                "w-2/5 pr-0 text-right @max-[560px]:mt-(--km-gap-row) @max-[560px]:w-auto @max-[560px]:text-left",
              )}
            >
              <Choice
                row={row}
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
