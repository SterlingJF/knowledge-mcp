// C-Proposal: the card for every kb_prepare_proposal result (knowledge-mcp/proposal/1).
// Inline it summarises the changes; the full view shows every change with its tick box.
// The card holds the kept set and the lifecycle, so both survive the display-mode switch.
import { useState } from "react";

import { useCardHost } from "@/bridge/bridge";
import { PathChip } from "@/component-elements/chips";
import type { KeyValueRow } from "@/component-elements/key-value";
import type { CardAction } from "@/component-patterns/card-shell";
import { useCardLifecycle } from "@/component-patterns/card-lifecycle";
import type { CardLifecycle } from "@/component-patterns/card-lifecycle";
import { ChangeTable } from "@/component-patterns/change-table";
import { FullView } from "@/component-patterns/full-view";
import { LeftOut } from "@/component-patterns/left-out";
import { SummaryCard } from "@/component-patterns/summary-card";
import type { EvidenceMark, Proposal } from "@/contracts/proposal";
import {
  action,
  badge,
  change,
  evidence,
  eyebrow,
  frozen,
  label,
  line,
  message,
} from "@/copy/en";
import { registerCard } from "./registry";
import type { CardProps } from "./registry";

const MARKS: EvidenceMark[] = [
  "supported",
  "partly",
  "conflicting",
  "suggested",
];
const MAX_ROWS = 4;

const numbers = (p: Proposal) => p.rows.map((_, i) => i + 1);

/** The last path segment of the subject, or "the document" without one. */
export function fileName(p: Proposal): string {
  return p.instance?.subject.split("/").at(-1) || "the document";
}

export function saveMessage(p: Proposal, kept: Set<number>): string {
  const out = numbers(p).filter((n) => !kept.has(n));
  return message.save(
    change.list([...kept]),
    fileName(p),
    out.length > 0 ? change.list(out) : undefined,
  );
}

export function saveContext(p: Proposal, kept: Set<number>) {
  return {
    proposal: {
      subject: p.instance?.subject,
      based_on: p.based_on,
      instance: p.instance,
      kept: [...kept].sort((a, b) => a - b),
    },
  };
}

/** A change's name: the section it touches, else its proposed text. */
const rowName = (p: Proposal, i: number) =>
  p.rows[i].current?.label ??
  p.rows[i].proposed.label ??
  p.rows[i].proposed.text;
const rowLabel = (p: Proposal, i: number) =>
  `${change.number(i + 1)} ${rowName(p, i)}`;

export function summaryRows(p: Proposal): KeyValueRow[] {
  const isNew = p.rows.every((r) => !r.current);
  const rows: KeyValueRow[] = [
    {
      label: isNew ? label.sections : label.changes,
      value: p.rows.map((_, i) => rowLabel(p, i)).join(line.summaryJoin),
    },
  ];
  const counts = MARKS.map(
    (mark) => [mark, p.rows.filter((r) => r.mark === mark).length] as const,
  ).filter(([, n]) => n > 0);
  if (counts.length > 0)
    rows.push({
      label: label.evidence,
      value: counts
        .map(([mark, n]) => `${n} ${evidence[mark].toLowerCase()}`)
        .join(line.summaryJoin),
    });
  const conflict = p.rows.findIndex((r) => r.mark === "conflicting");
  if (conflict >= 0)
    rows.push({
      label: label.needsYou,
      value: (
        <>
          <b>{rowLabel(p, conflict)}</b>
          {line.summaryJoin}
          {p.rows[conflict].proposed.text}
        </>
      ),
    });
  if (p.left_out && p.left_out.length > 0)
    rows.push({
      label: label.leftOut,
      value: p.left_out.map((f) => f.file).join(line.summaryJoin),
    });
  return rows.slice(0, MAX_ROWS);
}

export type ProposalViewProps = {
  proposal: Proposal;
  displayMode: "inline" | "fullscreen";
  kept: Set<number>;
  onKeptChange: (kept: Set<number>) => void;
  lifecycle: CardLifecycle;
};

/** The drawn card, given its state; the gallery renders it with fixed lifecycles. */
export function ProposalView({
  proposal: p,
  displayMode,
  kept,
  onKeptChange,
  lifecycle,
}: ProposalViewProps) {
  const isNew = p.rows.every((r) => !r.current);
  const file = fileName(p);
  const shell = {
    // Once pressed, the card is a record of one change, not a proposal.
    eyebrow:
      lifecycle.state === "frozen"
        ? eyebrow.change
        : isNew
          ? eyebrow.proposedDocument
          : eyebrow.proposedChanges,
    title: p.summary,
    meta: p.instance ? <PathChip path={file} /> : undefined,
    badge:
      lifecycle.frozenLine === frozen.approved
        ? { tone: "done" as const, label: badge.done.approved }
        : lifecycle.frozenLine === frozen.notSaved
          ? { tone: "neutral" as const, label: badge.neutral.notSaved }
          : { tone: "waiting" as const, label: badge.waiting.nothingSaved },
    why: line.waitsBecause(file),
    lifecycle,
  };
  const save: CardAction = {
    label: action.save(change.list([...kept])),
    message: saveMessage(p, kept),
    frozenLine: frozen.approved,
    variant: "primary",
    disabled: kept.size === 0,
    context: saveContext(p, kept),
  };
  const notNow: CardAction = {
    label: action.notNow,
    message: message.notNow,
    frozenLine: frozen.notSaved,
  };
  const actions = [save, notNow];

  if (displayMode === "fullscreen")
    return (
      <FullView {...shell} actions={actions}>
        <ChangeTable
          rows={p.rows}
          kept={kept}
          onKeptChange={lifecycle.state === "live" ? onKeptChange : undefined}
        />
        {p.left_out && <LeftOut files={p.left_out} />}
      </FullView>
    );
  return <SummaryCard {...shell} rows={summaryRows(p)} actions={actions} />;
}

function LiveProposal(props: Omit<ProposalViewProps, "lifecycle">) {
  const lifecycle = useCardLifecycle();
  return <ProposalView {...props} lifecycle={lifecycle} />;
}

export function ProposalCard({ result }: CardProps) {
  const proposal = result as unknown as Proposal;
  const host = useCardHost();
  const [kept, setKept] = useState(() => new Set(numbers(proposal)));
  return (
    <LiveProposal
      proposal={proposal}
      displayMode={host.displayMode}
      kept={kept}
      onKeptChange={setKept}
    />
  );
}

registerCard("knowledge-mcp/proposal/1", ProposalCard);
