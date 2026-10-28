// P02 Change table: one row per Cn — what is there now, what is proposed with its evidence mark, and the exact sources.
import type { ReactNode } from "react";

import { ChangeNumber, SelectAll } from "@/component-elements/change-number";
import { SourceChip } from "@/component-elements/chips";
import { EvidenceMark } from "@/component-elements/evidence-mark";
import { CurrentText } from "@/component-elements/text-lines";
import type { ProposalCell, ProposalRow, Source } from "@/contracts/proposal";
import { label as labels, line, source as sourceCopy } from "@/copy/en";
import { cn } from "@/lib/utils";

import { tableLabel, tableRow } from "./table-classes";

const headClass = cn(tableLabel, "@max-[560px]:sr-only");
// A left-out row: its text is struck and tertiary; the tick box stays at full strength.
const tertiary = "text-(--color-text-tertiary)";
// Only text spans are struck: a strike on the cell would reach the evidence mark.
const struck = "line-through";
const editCols =
  "grid-cols-[auto_minmax(0,29fr)_minmax(0,42fr)_minmax(0,29fr)]";
// Draft: Cn, Section, Draft, Source (D05F).
const draftCols = "grid-cols-[auto_auto_minmax(0,55fr)_minmax(0,45fr)]";

function Cell({
  label,
  text,
  className,
}: ProposalCell & { className?: string }) {
  return (
    <span className={className}>
      {label != null && (
        <span className="font-(--font-weight-semibold)">{label}:</span>
      )}
      {label != null && " "}
      {text}
    </span>
  );
}

function sameFileAsPrevious(sources: Source[], i: number): boolean {
  const here = sources[i];
  const before = sources[i - 1];
  return (
    before != null &&
    "line_number" in here &&
    "line_number" in before &&
    here.file === before.file
  );
}

function Sources({ sources }: { sources: Source[] }) {
  return (
    <span
      data-testid="sources"
      className="flex min-w-0 flex-col items-start gap-(--km-gap-tight)"
    >
      {sources.map((source, i) => {
        const short = sameFileAsPrevious(sources, i);
        return (
          <span
            key={i}
            className="flex max-w-full min-w-0 items-center gap-(--km-gap-inline)"
          >
            {short && (
              <span className="text-(--color-text-tertiary)">
                {sourceCopy.versus}
              </span>
            )}
            <SourceChip
              source={source}
              continuation={short}
              className="max-w-full min-w-0 whitespace-normal wrap-anywhere"
            />
          </span>
        );
      })}
    </span>
  );
}

export type ChangeTableProps = {
  /** Row n (from 1) is change Cn. */
  rows: ProposalRow[];
  /** Numbers of the changes kept. Ignored when frozen. */
  kept?: Set<number>;
  /** Omit for a frozen table: numbers stay, boxes go. */
  onKeptChange?: (kept: Set<number>) => void;
  /** A proposed new document: no Current column, no boxes, every section kept. */
  draft?: boolean;
  className?: string;
};

export function ChangeTable({
  rows,
  kept,
  onKeptChange,
  draft = false,
  className,
}: ChangeTableProps) {
  const frozen = draft || onKeptChange == null;
  const rowClass = cn(tableRow, draft ? draftCols : editCols);
  const keptSet = kept ?? new Set(rows.map((_, i) => i + 1));
  const isKept = (n: number) => frozen || keptSet.has(n);

  const setOne = (n: number, keep: boolean) => {
    const next = new Set(keptSet);
    if (keep) next.add(n);
    else next.delete(n);
    onKeptChange?.(next);
  };

  let head: ReactNode = <span />;
  if (!frozen && onKeptChange)
    head = (
      <SelectAll
        keptCount={rows.filter((_, i) => keptSet.has(i + 1)).length}
        total={rows.length}
        onChange={(all) =>
          onKeptChange(new Set(all ? rows.map((_, i) => i + 1) : []))
        }
      />
    );

  return (
    <div
      role="table"
      className={cn(
        "@container text-(length:--font-text-sm-size) leading-(--font-text-sm-line-height) text-(--color-text-primary)",
        className,
      )}
    >
      <div role="row" className={cn(rowClass, "pt-0 pb-(--km-gap-row)")}>
        <span role="columnheader">{head}</span>
        <span role="columnheader" className={headClass}>
          {draft ? labels.section : labels.current}
        </span>
        <span role="columnheader" className={headClass}>
          {draft ? labels.draft : labels.proposed}
        </span>
        <span role="columnheader" className={headClass}>
          {labels.source}
        </span>
      </div>
      {rows.map((row, i) => {
        const n = i + 1;
        const out = !isKept(n);
        return (
          <div
            role="row"
            key={n}
            data-left-out={out || undefined}
            className={rowClass}
          >
            <span role="cell">
              <ChangeNumber
                n={n}
                kept={!out}
                onKeptChange={frozen ? undefined : (keep) => setOne(n, keep)}
              />
            </span>
            <span role="cell" className={cn(out && tertiary)}>
              {draft ? (
                <span className="whitespace-nowrap">{row.proposed.label}</span>
              ) : row.current ? (
                <CurrentText
                  label={row.current.label ?? labels.current}
                  className={cn(out && struck)}
                >
                  {row.current.text}
                </CurrentText>
              ) : (
                <span className={cn(tertiary, out && struck)}>
                  {line.addition}
                </span>
              )}
            </span>
            <span
              role="cell"
              className={cn(
                "flex flex-col gap-(--km-gap-tight)",
                out && tertiary,
                out && "[&_[data-mark]]:text-(--color-text-tertiary)",
              )}
            >
              {row.mark && <EvidenceMark mark={row.mark} />}
              {draft ? (
                <span>{row.proposed.text}</span>
              ) : (
                <Cell {...row.proposed} className={cn(out && struck)} />
              )}
            </span>
            <span
              role="cell"
              className={cn(
                out &&
                  "text-(--color-text-tertiary) [&_*]:text-(--color-text-tertiary)",
              )}
            >
              <Sources sources={row.sources} />
            </span>
          </div>
        );
      })}
    </div>
  );
}
