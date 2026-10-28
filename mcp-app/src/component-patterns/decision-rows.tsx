// P04 Decision rows: each row needs its own answer; decided rows show a badge in place of the choice.
import type { ReactNode } from "react";

import { Badge } from "@/component-elements/badge";
import type { BadgeTone } from "@/component-elements/badge";
import { SegmentedChoice } from "@/component-elements/segmented-choice";
import { decision } from "@/copy/en";
import { cn } from "@/lib/utils";

export type DecisionKind = "acceptDrop" | "applyKeepRefused";
export type DecisionValue = "accept" | "drop" | "apply" | "keepRefused";

const optionsFor = {
  acceptDrop: [
    { value: "accept", label: decision.accept },
    { value: "drop", label: decision.drop },
  ],
  applyKeepRefused: [
    { value: "apply", label: decision.apply },
    { value: "keepRefused", label: decision.keepRefused },
  ],
} as const;

export type DecisionRow = {
  id: string;
  /** Names the row for its choice's accessible label. */
  name: string;
  cells: ReactNode[];
  /** Set once the decision is recorded: the badge replaces the choice. Label comes from copy. */
  decided?: { tone: BadgeTone; label: string };
};

/** How many rows will be saved: the count for the card's primary button. */
export function countAccepted(
  choices: Record<string, DecisionValue | null>,
): number {
  return Object.values(choices).filter((v) => v === "accept" || v === "apply")
    .length;
}

export function DecisionRows({
  headers,
  rows,
  kind = "acceptDrop",
  choices,
  onChoiceChange,
  className,
}: {
  headers: ReactNode[];
  rows: DecisionRow[];
  kind?: DecisionKind;
  /** Owned by the parent; null or absent means undecided. */
  choices: Record<string, DecisionValue | null>;
  onChoiceChange: (id: string, value: DecisionValue) => void;
  className?: string;
}) {
  const cell = "py-(--km-space-4) pr-(--km-space-5) align-top";
  return (
    <table
      className={cn(
        "w-full border-collapse text-(length:--font-text-sm-size) leading-(--font-text-sm-line-height) text-(--color-text-primary)",
        className,
      )}
    >
      <thead>
        <tr className="border-b-(length:--border-width-regular) border-(--color-border-tertiary) text-left text-(length:--font-text-xs-size) leading-(--font-text-xs-line-height) font-(--font-weight-semibold) text-(--color-text-secondary)">
          {headers.map((h, i) => (
            <th key={i} className={cn(cell, "py-(--km-space-3) font-inherit")}>
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
            className="border-b-(length:--border-width-regular) border-(--color-border-tertiary) last:border-b-0"
          >
            {row.cells.map((c, i) => (
              <td key={i} className={cell}>
                {c}
              </td>
            ))}
            <td className={cn(cell, "pr-0 text-right")}>
              {row.decided ? (
                <Badge tone={row.decided.tone}>{row.decided.label}</Badge>
              ) : (
                <SegmentedChoice<DecisionValue>
                  aria-label={row.name}
                  options={optionsFor[kind]}
                  value={choices[row.id] ?? null}
                  onValueChange={(v) => onChoiceChange(row.id, v)}
                />
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
