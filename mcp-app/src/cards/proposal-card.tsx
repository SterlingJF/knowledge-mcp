// C-Proposal: the card for every kb_prepare_proposal result (knowledge-mcp/proposal/1).
// Inline it summarises the changes; the full view shows every change with its tick box.
// The card holds the kept set and the lifecycle, so both survive the display-mode switch.
import { useState } from "react";

import { useCardHost } from "@/bridge/bridge";
import type { ToolResult } from "@/bridge/bridge";
import { Badge } from "@/component-elements/badge";
import { NoBreakName, PathChip } from "@/component-elements/chips";
import { Note } from "@/component-patterns/note";
import type { KeyValueRow } from "@/component-elements/key-value";
import type { CardAction } from "@/component-patterns/card-shell";
import { useCardLifecycle } from "@/component-patterns/card-lifecycle";
import type { CardLifecycle } from "@/component-patterns/card-lifecycle";
import { ChangeTable } from "@/component-patterns/change-table";
import { FullView } from "@/component-patterns/full-view";
import { LeftOut } from "@/component-patterns/left-out";
import { SummaryCard } from "@/component-patterns/summary-card";
import type {
  EvidenceMark,
  Proposal,
  ProposalCell,
} from "@/contracts/proposal";
import {
  action,
  badge,
  change,
  evidenceCount,
  eyebrow,
  frozen,
  label,
  line,
  message,
  proposal as proposalCopy,
} from "@/copy/en";
import { lastSegment } from "./file-name";
import { registerCard } from "./registry";
import type { CardProps } from "./registry";

const MARKS: EvidenceMark[] = [
  "supported",
  "partly",
  "conflicting",
  "suggested",
];
const MAX_ROWS = 4;
/** More changes than this and the summary counts them instead of naming them. */
const MAX_NAMED = 4;

/** Which of the two actions was pressed; undefined while live. */
export type Pressed = "save" | "notNow";

const numbers = (p: Proposal) => p.rows.map((_, i) => i + 1);

export function isProposal(
  result: ToolResult | null,
): result is ToolResult & Proposal {
  if (!result || result.schema !== "knowledge-mcp/proposal/1") return false;
  const { summary, rows } = result as Partial<Proposal>;
  return (
    typeof summary === "string" &&
    Array.isArray(rows) &&
    rows.every(
      (r) =>
        typeof r === "object" &&
        r !== null &&
        typeof r.proposed?.text === "string" &&
        Array.isArray(r.sources),
    )
  );
}

export const isNewDocument = (p: Proposal) => p.rows.every((r) => !r.current);

/** The last path segment of the subject, or "the document" without one. */
export function fileName(p: Proposal): string {
  return lastSegment(p.instance?.subject ?? "") || line.theDocument;
}

export function saveMessage(p: Proposal, kept: Set<number>): string {
  if (isNewDocument(p))
    return message.create(
      p.instance?.subject ?? line.theDocument,
      change.list([...kept]),
    );
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

const HEAD_CHARS = 24;

/** Text cut at a word to a short head, with an ellipsis when cut. */
function head(text: string): string {
  if (text.length <= HEAD_CHARS) return text;
  const cut = text.slice(0, HEAD_CHARS + 1);
  const space = cut.lastIndexOf(" ");
  return `${(space > 0 ? cut.slice(0, space) : cut.slice(0, HEAD_CHARS)).replace(/[\s.,;:]+$/, "")}${proposalCopy.ellipsis}`;
}

/** A change's label, from the document or the proposal, when either has one. */
const rowLabelOnly = (p: Proposal, i: number) =>
  p.rows[i].current?.label ?? p.rows[i].proposed.label;

/** A change's name: the section it touches, else a short head of its proposed text. */
const rowName = (p: Proposal, i: number) =>
  rowLabelOnly(p, i) ?? head(p.rows[i].proposed.text);
const rowLabel = (p: Proposal, i: number) =>
  `${change.number(i + 1)} ${rowName(p, i)}`;

/** `saved`: the changes a frozen Save kept; the Changes row then names only those. */
export function summaryRows(p: Proposal, saved?: Set<number>): KeyValueRow[] {
  const isNew = isNewDocument(p);
  const named = numbers(p).filter((n) => !saved || saved.has(n));
  const rows: KeyValueRow[] = [
    {
      label: isNew ? label.sections : label.changes,
      value:
        named.length > MAX_NAMED
          ? change.count(named.length)
          : named.map((n) => rowLabel(p, n - 1)).join(line.summaryJoin),
    },
  ];
  const counts = MARKS.map(
    (mark) => [mark, p.rows.filter((r) => r.mark === mark).length] as const,
  ).filter(([, n]) => n > 0);
  if (counts.length > 0)
    rows.push({
      label: label.evidence,
      value: counts
        .map(([mark, n]) => line.counted(n, evidenceCount[mark]))
        .join(line.summaryJoin),
    });
  const savedAs = p.filing?.path ?? (isNew ? p.instance?.subject : undefined);
  if (savedAs)
    rows.push({
      label: label.savedAs,
      value: p.filing
        ? [
            savedAs,
            p.filing.naming_rule === null
              ? proposalCopy.noNamingRule
              : proposalCopy.namedBy(p.filing.naming_rule),
          ].join(line.summaryJoin)
        : savedAs,
    });
  const conflicts = p.rows.flatMap((r, i) =>
    r.mark === "conflicting" ? [i] : [],
  );
  if (conflicts.length > 0) {
    const [first] = conflicts;
    rows.push({
      label: label.needsYou,
      value: (
        <>
          <b>
            {[change.number(first + 1), rowLabelOnly(p, first)]
              .filter(Boolean)
              .join(" ")}
          </b>
          {line.summaryJoin}
          {p.rows[first].proposed.text}
          {conflicts.length > 1 &&
            `${line.summaryJoin}${line.andMore(conflicts.length - 1)}`}
        </>
      ),
    });
  } else if (p.open_questions && p.open_questions.length > 0) {
    rows.push({
      label: label.needsYou,
      value: openQuestion(p.open_questions),
    });
  }
  if (!isNew && p.left_out && p.left_out.length > 0)
    rows.push({
      label: label.leftOut,
      value: p.left_out.map((f) => f.file).join(line.summaryJoin),
    });
  return rows.slice(0, MAX_ROWS);
}

/** An open question as `Rollout owner · no source`. */
const unsourced = (q: ProposalCell) =>
  proposalCopy.unsourced(q.label ?? q.text);

/** The first open question, then `+n more`. */
function openQuestion(questions: ProposalCell[]): string {
  const [first] = questions;
  return [
    unsourced(first),
    ...(questions.length > 1 ? [line.andMore(questions.length - 1)] : []),
  ].join(line.summaryJoin);
}

const hasMeta = (p: Proposal) =>
  Boolean(p.filing ?? p.instance ?? p.document_type ?? p.reader);

/** File chip, document type, reader, and a badge when the reader is a guess. */
function MetaLine({ p, full }: { p: Proposal; full: boolean }) {
  const where = p.filing?.path ?? p.instance?.subject;
  const words = [
    p.document_type?.label,
    p.reader && proposalCopy.forReader(p.reader.label),
  ].filter((w): w is string => w != null);
  return (
    <>
      {where && (
        <PathChip path={where.split("/").at(-1) || where} title={where} />
      )}
      {words.length > 0 && <span>{words.join(line.summaryJoin)}</span>}
      {p.reader && !p.reader.confirmed && (
        <Badge tone="neutral">
          {full ? proposalCopy.readerGuess : proposalCopy.guess}
        </Badge>
      )}
    </>
  );
}

export type ProposalViewProps = {
  proposal: Proposal;
  displayMode: "inline" | "fullscreen";
  kept: Set<number>;
  onKeptChange: (kept: Set<number>) => void;
  lifecycle: CardLifecycle;
  pressed?: Pressed;
  /** Told which action was pressed, before the lifecycle freezes the card. */
  onPressed?: (pressed: Pressed) => void;
};

/** The drawn card, given its state; the gallery renders it with fixed lifecycles. */
export function ProposalView({
  proposal: p,
  displayMode,
  kept,
  onKeptChange,
  lifecycle,
  pressed,
  onPressed,
}: ProposalViewProps) {
  const isNew = isNewDocument(p);
  const live = lifecycle.state === "live";
  const shell = {
    // Once pressed or replaced, the card is a record of one change, not a proposal.
    eyebrow: !live
      ? eyebrow.change
      : isNew
        ? eyebrow.proposedDocument
        : eyebrow.proposedChanges,
    title: p.summary,
    meta: hasMeta(p) ? (
      <MetaLine p={p} full={displayMode === "fullscreen"} />
    ) : undefined,
    badge:
      pressed === "save"
        ? { tone: "done" as const, label: badge.done.approved }
        : pressed === "notNow"
          ? { tone: "neutral" as const, label: badge.neutral.notSaved }
          : { tone: "waiting" as const, label: badge.waiting.nothingSaved },
    why: isNew ? undefined : line.waitsBecause(fileName(p)),
  };
  // A new document is created whole: every section goes.
  const sending = isNew ? new Set(numbers(p)) : kept;
  const save: CardAction = {
    label: isNew ? action.createFile : action.save(change.list([...kept])),
    message: saveMessage(p, sending),
    frozenLine: frozen.approved,
    variant: "default",
    disabled: sending.size === 0,
    context: saveContext(p, sending),
  };
  const notNow: CardAction = {
    label: action.notNow,
    message: message.notNow,
    frozenLine: frozen.notSaved,
  };
  const actions = [save, notNow];
  const tracked: CardLifecycle = {
    ...lifecycle,
    press: (a) => {
      const kind: Pressed = a === notNow ? "notNow" : "save";
      if (lifecycle.state === "live" && !a.disabled) onPressed?.(kind);
      // Saved with the frozen state, so a remount redraws what the person kept.
      const extra: PressedState = { kept: [...kept], pressed: kind };
      lifecycle.press(a, extra);
    },
  };
  const card = { ...shell, lifecycle: tracked, actions };

  if (displayMode === "fullscreen")
    return (
      <FullView {...card}>
        <ChangeTable
          draft={isNew}
          rows={p.rows}
          kept={kept}
          onKeptChange={live ? onKeptChange : undefined}
        />
        {p.filing?.naming_rule === null && (
          <Note
            kind="info"
            fact={proposalCopy.noRuleFor(p.document_type?.label)}
          >
            <NoBreakName>{p.filing.reason}</NoBreakName>
          </Note>
        )}
        {p.open_questions && p.open_questions.length > 0 && (
          <Note
            kind="leftOut"
            fact={proposalCopy.toAnswer(p.open_questions.length)}
          >
            {proposalCopy.openList(p.open_questions.map(unsourced))}{" "}
            {proposalCopy.staysOpen(p.open_questions.length)}
          </Note>
        )}
        {p.left_out && p.left_out.length > 0 && <LeftOut files={p.left_out} />}
      </FullView>
    );
  return (
    <SummaryCard
      {...card}
      rows={summaryRows(p, pressed === "save" ? kept : undefined)}
    />
  );
}

/** What a press saves with the frozen state, given back as `lifecycle.restored`. */
type PressedState = { kept: number[]; pressed: Pressed };

function isPressedState(value: unknown): value is PressedState {
  return (
    typeof value === "object" &&
    value !== null &&
    "kept" in value &&
    Array.isArray(value.kept) &&
    value.kept.every((n) => typeof n === "number") &&
    "pressed" in value &&
    (value.pressed === "save" || value.pressed === "notNow")
  );
}

function LiveProposal({ proposal }: { proposal: Proposal }) {
  const host = useCardHost();
  const lifecycle = useCardLifecycle();
  const restored = isPressedState(lifecycle.restored)
    ? lifecycle.restored
    : undefined;
  const [kept, setKept] = useState(
    () => new Set(restored?.kept ?? numbers(proposal)),
  );
  const [pressed, setPressed] = useState<Pressed | undefined>(
    restored?.pressed,
  );
  return (
    <ProposalView
      proposal={proposal}
      displayMode={host.displayMode}
      kept={kept}
      onKeptChange={setKept}
      lifecycle={lifecycle}
      pressed={pressed}
      onPressed={setPressed}
    />
  );
}

export function ProposalCard({ result }: CardProps) {
  if (!isProposal(result)) return null;
  const i = result.instance;
  // A new result starts over: its kept set is derived afresh.
  const key = i ? `${i.subject}|${i.created_at}|${i.seq}` : result.summary;
  return <LiveProposal key={key} proposal={result} />;
}

registerCard("knowledge-mcp/proposal/1", ProposalCard);
