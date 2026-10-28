// C-Move: the card for a kb_prepare_document_moves plan (knowledge-mcp/document-moves/1).
// Inline it summarises the plan; the full view lists every move and link and takes the
// blocker answers. The card holds the answers and the lifecycle, so both survive the switch.
// The server opens no file: Approve only sends the person's message, and the assistant moves.
import { useState } from "react";

import { useCardHost } from "@/bridge/bridge";
import type { ToolResult } from "@/bridge/bridge";
import { PathChip } from "@/component-elements/chips";
import type { KeyValueRow } from "@/component-elements/key-value";
import type { CardAction } from "@/component-patterns/card-shell";
import { useCardLifecycle } from "@/component-patterns/card-lifecycle";
import type { CardLifecycle } from "@/component-patterns/card-lifecycle";
import { ChangeTable } from "@/component-patterns/change-table";
import { DecisionRows } from "@/component-patterns/decision-rows";
import type { DecisionValue } from "@/component-patterns/decision-rows";
import { FullView } from "@/component-patterns/full-view";
import { SummaryCard } from "@/component-patterns/summary-card";
import type { DocumentMoves, MoveIssue } from "@/contracts/document-moves";
import { action, badge, frozen, line, message, moves } from "@/copy/en";
import { registerCard } from "./registry";
import type { CardProps } from "./registry";

export type Pressed = "move" | "notNow";
export type Answers = Record<string, DecisionValue | null>;

const STATUSES = ["permission_needed", "ready", "blocked"];

export function isMovePlan(
  result: ToolResult | null,
): result is ToolResult & DocumentMoves {
  if (!result || result.schema !== "knowledge-mcp/document-moves/1")
    return false;
  const r = result as Partial<DocumentMoves>;
  const pair = (m: unknown) =>
    typeof m === "object" &&
    m !== null &&
    typeof (m as { path?: unknown }).path === "string" &&
    typeof (m as { old_path?: unknown }).old_path === "string";
  return (
    typeof r.location === "string" &&
    // texts_needed and unchanged carry no plan for the person to approve.
    STATUSES.includes(r.status as string) &&
    Array.isArray(r.moves) &&
    r.moves.length > 0 &&
    r.moves.every(pair) &&
    Array.isArray(r.links) &&
    r.links.every((l) => typeof l?.source_path === "string") &&
    Array.isArray(r.issues) &&
    typeof r.based_on === "object" &&
    r.based_on !== null
  );
}

const dir = (path: string) => {
  const i = path.lastIndexOf("/");
  return i < 0 ? moves.root : path.slice(0, i + 1);
};
const base = (path: string) => path.split("/").at(-1) ?? path;
const unique = (xs: string[]) => [...new Set(xs)];

/** Issues stop the plan only when it is blocked; otherwise there are none. */
export const blockers = (p: DocumentMoves): MoveIssue[] =>
  p.status === "blocked" ? p.issues : [];
const issueId = (i: number) => `b${i + 1}`;

export const repairedLinks = (p: DocumentMoves) =>
  p.links.filter((l) => l.replacement !== null);
const linkNotes = (p: DocumentMoves) =>
  unique(repairedLinks(p).map((l) => l.source_path)).length;

export const allAnswered = (p: DocumentMoves, answers: Answers) =>
  blockers(p).every((_, i) => answers[issueId(i)] != null);

export function summaryRows(p: DocumentMoves): KeyValueRow[] {
  const from = unique(p.moves.map((m) => dir(m.old_path))).join(", ");
  const to = unique(p.moves.map((m) => dir(m.path))).join(", ");
  const rows: KeyValueRow[] = [
    {
      label: moves.label.moves,
      value: moves.movesValue(p.moves.length, from, to),
    },
  ];
  const renames = p.moves.filter((m) => base(m.old_path) !== base(m.path));
  if (renames.length > 0)
    rows.push({
      label: moves.label.renames,
      value: moves.count(renames.length),
    });
  const repaired = repairedLinks(p).length;
  if (repaired > 0)
    rows.push({
      label: moves.label.links,
      value: moves.linksValue(repaired, linkNotes(p)),
    });
  const b = blockers(p);
  if (b.length > 0)
    rows.push({
      label: moves.label.blockers,
      value: (
        <>
          <b>{moves.blockersValue(b.length)}</b>
          {line.summaryJoin}
          {unique(b.map((i) => i.code)).join(line.summaryJoin)}
        </>
      ),
    });
  return rows;
}

export function moveContext(p: DocumentMoves, answers: Answers) {
  return {
    document_moves: {
      location: p.location,
      status: p.status,
      moves: p.moves,
      based_on: p.based_on,
      digest: p.digest,
      blockers: blockers(p).map((issue, i) => ({
        ...issue,
        answer: answers[issueId(i)] ?? null,
      })),
    },
  };
}

export type MoveViewProps = {
  plan: DocumentMoves;
  displayMode: "inline" | "fullscreen";
  answers: Answers;
  onAnswer: (id: string, value: DecisionValue) => void;
  lifecycle: CardLifecycle;
  pressed?: Pressed;
  onPressed?: (pressed: Pressed) => void;
};

export function MoveView({
  plan: p,
  displayMode,
  answers,
  onAnswer,
  lifecycle,
  pressed,
  onPressed,
}: MoveViewProps) {
  const live = lifecycle.state === "live";
  const b = blockers(p);
  const repaired = repairedLinks(p);
  const shell = {
    eyebrow: live ? moves.eyebrow : moves.eyebrowDone,
    title: moves.title,
    meta: <PathChip path={p.location} />,
    badge:
      pressed === "move"
        ? { tone: "done" as const, label: badge.done.approved }
        : pressed === "notNow"
          ? { tone: "neutral" as const, label: badge.neutral.notMoved }
          : b.length > 0
            ? { tone: "waiting" as const, label: badge.waiting.needsChoice }
            : { tone: "waiting" as const, label: badge.waiting.needsOk },
    why: !live
      ? undefined
      : b.length > 0
        ? moves.whyBlocked
        : moves.why(linkNotes(p)),
  };
  const move: CardAction = {
    label: action.move(p.moves.length),
    message: moves.message(p.moves.length, repaired.length),
    frozenLine: frozen.approved,
    variant: "primary",
    disabled: !allAnswered(p, answers),
    context: moveContext(p, answers),
  };
  const notNow: CardAction = {
    label: action.notNow,
    message: message.notNow,
    frozenLine: frozen.notMoved,
  };
  const tracked: CardLifecycle = {
    ...lifecycle,
    press: (a) => {
      if (lifecycle.state === "live" && !a.disabled)
        onPressed?.(a === notNow ? "notNow" : "move");
      lifecycle.press(a);
    },
  };
  const card = { ...shell, lifecycle: tracked, actions: [move, notNow] };

  if (displayMode === "fullscreen")
    return (
      <FullView {...card}>
        {b.length > 0 && (
          <DecisionRows
            headers={[moves.label.problem]}
            rows={b.map((issue, i) => ({
              id: issueId(i),
              name: issue.detail,
              cells: [
                <>
                  <b>{issue.source_path ?? issue.code}</b>
                  {line.summaryJoin}
                  {issue.detail}
                </>,
              ],
            }))}
            choices={answers}
            onChoiceChange={live ? onAnswer : () => {}}
          />
        )}
        <ChangeTable
          draft
          rows={p.moves.map((m) => ({
            proposed: { label: m.old_path, text: m.path },
            sources: [],
          }))}
        />
        {p.links.length > 0 && (
          <ChangeTable
            rows={p.links.map((l) => ({
              current: { label: l.source_path, text: l.target_before },
              proposed: { text: l.replacement ?? l.target_after },
              sources: [],
            }))}
          />
        )}
      </FullView>
    );
  return <SummaryCard {...card} rows={summaryRows(p)} />;
}

function LiveMove({ plan }: { plan: DocumentMoves }) {
  const host = useCardHost();
  const [answers, setAnswers] = useState<Answers>({});
  const [pressed, setPressed] = useState<Pressed>();
  const lifecycle = useCardLifecycle();
  return (
    <MoveView
      plan={plan}
      displayMode={host.displayMode}
      answers={answers}
      onAnswer={(id, v) => setAnswers((a) => ({ ...a, [id]: v }))}
      lifecycle={lifecycle}
      pressed={pressed}
      onPressed={setPressed}
    />
  );
}

export function MoveCard({ result }: CardProps) {
  if (!isMovePlan(result)) return null;
  // A new plan starts over: its answers are derived afresh.
  const key = `${result.location}|${result.based_on.listing_digest}|${result.digest}`;
  return <LiveMove key={key} plan={result} />;
}

registerCard("knowledge-mcp/document-moves/1", MoveCard);
