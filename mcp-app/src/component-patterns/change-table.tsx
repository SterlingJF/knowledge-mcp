// P02 Change table: one row per Cn — what is there now, what is proposed with its evidence mark, and the exact sources.
import { ChangeNumber, SelectAll } from "@/component-patterns/change-number";
import { SourceChip } from "@/component-elements/chips";
import { EvidenceMark } from "@/component-elements/evidence-mark";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/component-elements/table";
import { CurrentText } from "@/component-elements/text-lines";
import type { ProposalCell, ProposalRow, Source } from "@/contracts/proposal";
import { label as labels, line, source as sourceCopy } from "@/copy/en";
import { cn } from "@/lib/utils";

function Cell({
  label,
  text,
  className,
}: ProposalCell & { className?: string }) {
  return (
    <span className={className}>
      {label != null && <span className="font-semibold">{label}:</span>}
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
    <span data-testid="sources" className="flex min-w-0 flex-col gap-1">
      {sources.map((source, i) => {
        const short = sameFileAsPrevious(sources, i);
        return (
          <span key={i} className="flex min-w-0 items-baseline gap-1">
            {short && (
              <span className="text-xs text-muted-foreground">
                {sourceCopy.versus}
              </span>
            )}
            <SourceChip source={source} continuation={short} />
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
  const keptSet = kept ?? new Set(rows.map((_, i) => i + 1));
  // A frozen table given `kept` still shows what was left out; without it every row reads as kept.
  const isKept = (n: number) => draft || keptSet.has(n);

  const setOne = (n: number, keep: boolean) => {
    const next = new Set(keptSet);
    if (keep) next.add(n);
    else next.delete(n);
    onKeptChange?.(next);
  };

  return (
    <Table className={className}>
      <TableHeader>
        <TableRow>
          <TableHead className="w-16">
            {!draft && onKeptChange && (
              <SelectAll
                keptCount={rows.filter((_, i) => keptSet.has(i + 1)).length}
                total={rows.length}
                onChange={(all) =>
                  onKeptChange(new Set(all ? rows.map((_, i) => i + 1) : []))
                }
              />
            )}
          </TableHead>
          <TableHead className={draft ? "w-1/5" : "w-1/4"}>
            {draft ? labels.section : labels.current}
          </TableHead>
          <TableHead>{draft ? labels.draft : labels.proposed}</TableHead>
          <TableHead className="w-1/4">{labels.source}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row, i) => {
          const n = i + 1;
          const out = !isKept(n);
          return (
            <TableRow key={n} data-left-out={out || undefined}>
              <TableCell>
                <ChangeNumber
                  n={n}
                  kept={!out}
                  onKeptChange={frozen ? undefined : (keep) => setOne(n, keep)}
                />
              </TableCell>
              <TableCell>
                {draft ? (
                  <span className="font-semibold">{row.proposed.label}</span>
                ) : row.current?.label != null ? (
                  <CurrentText label={row.current.label} struck={out}>
                    {row.current.text}
                  </CurrentText>
                ) : (
                  <span
                    className={cn(
                      "text-muted-foreground",
                      out && "line-through",
                    )}
                  >
                    {row.current?.text ?? line.addition}
                  </span>
                )}
              </TableCell>
              <TableCell>
                <span className="flex flex-col gap-1">
                  {draft ? (
                    <span>{row.proposed.text}</span>
                  ) : (
                    <Cell
                      {...row.proposed}
                      className={cn(out && "line-through")}
                    />
                  )}
                  {row.mark && <EvidenceMark mark={row.mark} />}
                </span>
              </TableCell>
              <TableCell>
                <Sources sources={row.sources} />
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
