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
import { Note } from "@/component-elements/note";
import { Tabs } from "@/component-elements/tabs";
import { DecisionRows } from "@/component-patterns/decision-rows";
import { FullView } from "@/component-patterns/full-view";
import { PlanLines, PlanTable } from "@/component-patterns/plan-table";
import { SummaryCard } from "@/component-patterns/summary-card";
import type {
  DocumentMoves,
  MoveChoice,
  MoveIssue,
} from "@/contracts/document-moves";
import { action, badge, frozen, label, line, message, moves } from "@/copy/en";
import { registerCard } from "./registry";
import type { CardProps } from "./registry";

export type Pressed = "move" | "notNow";
/** Blocker id to the index of the chosen choice. */
export type Answers = Record<string, string | null>;

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
const LINK_LIMIT = 3;
const unique = (xs: string[]) => [...new Set(xs)];

/** Issues stop the plan only when it is blocked; otherwise there are none. */
export const blockers = (p: DocumentMoves): MoveIssue[] =>
  p.status === "blocked" ? p.issues : [];
const issueId = (i: number) => `b${i + 1}`;

export const repairedLinks = (p: DocumentMoves) =>
  p.links.filter((l) => l.replacement !== null);
const linkNotes = (p: DocumentMoves) =>
  unique(repairedLinks(p).map((l) => l.source_path)).length;

/** A blocker with no computed choice can only be answered in chat. */
const answerable = (issue: MoveIssue) => (issue.choices?.length ?? 0) > 0;

export const allAnswered = (p: DocumentMoves, answers: Answers) =>
  blockers(p).every(
    (issue, i) => answerable(issue) && answers[issueId(i)] != null,
  );

const choiceLabel = (c: MoveChoice) =>
  c.action === "skip_move"
    ? moves.skipFile
    : moves.linkTo(c.path.replace(/\.md$/, ""));

const fromFolder = (p: DocumentMoves) =>
  p.folder ?? unique(p.moves.map((m) => dir(m.old_path))).join(", ");

export function summaryRows(p: DocumentMoves): KeyValueRow[] {
  const to = unique(p.moves.map((m) => dir(m.path))).join(", ");
  const rows: KeyValueRow[] = [
    {
      label: moves.label.moves,
      value: moves.movesValue(p.moves.length, fromFolder(p), to),
    },
  ];
  const renames = p.moves.filter((m) => base(m.old_path) !== base(m.path));
  if (renames.length > 0) {
    const rules = unique(
      renames.map((m) => p.naming?.find((n) => n.path === m.path)?.rule ?? ""),
    );
    rows.push({
      label: moves.label.renames,
      value: moves.renamesValue(
        renames.length,
        rules.length === 1 && rules[0] ? rules[0] : undefined,
      ),
    });
  }
  const repaired = repairedLinks(p).length;
  if (repaired > 0)
    rows.push({
      label: moves.label.links,
      value: moves.linksValue(repaired, linkNotes(p)),
    });
  const b = blockers(p);
  const stays = p.stays ?? [];
  if (b.length > 0)
    rows.push({
      label: label.needsYou,
      value: (
        <>
          <b>{moves.blockersValue(b.length)}</b>
          {line.summaryJoin}
          {unique(b.map((i) => i.code)).join(", ")}
        </>
      ),
    });
  else if (stays.length > 0)
    rows.push({
      label: moves.label.stays,
      value:
        moves.staysValue(base(stays[0].path), stays[0].reason) +
        (stays.length > 1
          ? `${line.summaryJoin}${line.andMore(stays.length - 1)}`
          : ""),
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
        answer: issue.choices?.[Number(answers[issueId(i)])] ?? null,
      })),
    },
  };
}

export type MoveViewProps = {
  plan: DocumentMoves;
  displayMode: "inline" | "fullscreen";
  answers: Answers;
  onAnswer: (id: string, value: string | null) => void;
  lifecycle: CardLifecycle;
  pressed?: Pressed;
  onPressed?: (pressed: Pressed) => void;
  /** The full view's first tab; the gallery opens Links. */
  defaultTab?: "moves" | "links";
};

export function MoveView({
  plan: p,
  displayMode,
  answers,
  onAnswer,
  lifecycle,
  pressed,
  onPressed,
  defaultTab,
}: MoveViewProps) {
  const live = lifecycle.state === "live";
  const b = blockers(p);
  const repaired = repairedLinks(p);
  const shell = {
    eyebrow: live ? moves.eyebrow : moves.eyebrowDone,
    title: p.summary ?? moves.title,
    meta: (
      <>
        <PathChip folder path={p.folder ?? p.location} />
        <span>
          {line.counted(
            p.moves.length + (p.stays?.length ?? 0),
            moves.newFiles,
          )}
        </span>
      </>
    ),
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
        {b.length > 0 ? (
          <DecisionRows
            headers={[moves.label.problem, moves.label.yourChoice]}
            align="start"
            // No title: the bold file name in the cell carries the weight.
            narrow={{ title: -1 }}
            choices={answers}
            onChoiceChange={(id, v) => live && onAnswer(id, v)}
            rows={b.map((issue, i) => ({
              id: issueId(i),
              name: issue.detail,
              cells: [
                <>
                  {issue.source_path && <b>{issue.source_path} </b>}
                  {issue.detail}
                </>,
              ],
              options: (issue.choices ?? []).map((c, n) => ({
                value: String(n),
                label: choiceLabel(c),
              })),
              // P04 draws no empty choice: with nothing to pick, the answer goes in chat.
              decided: answerable(issue)
                ? undefined
                : { tone: "neutral" as const, label: badge.neutral.nothingYet },
            }))}
          />
        ) : (
          <Tabs
            defaultValue={defaultTab}
            tabs={[
              {
                value: "moves",
                label: moves.label.moves,
                count: p.moves.length,
                content: <MovesTable plan={p} />,
              },
              {
                value: "links",
                label: moves.label.links,
                count: repaired.length,
                content: <LinksTable plan={p} />,
              },
            ]}
          />
        )}
      </FullView>
    );
  return <SummaryCard {...card} rows={summaryRows(p)} />;
}

function MovesTable({ plan: p }: { plan: DocumentMoves }) {
  const stays = p.stays ?? [];
  return (
    <div className="flex flex-col gap-(--km-gap-group)">
      <PlanTable
        headers={[moves.label.file, moves.label.goesTo]}
        columns={[45, 55]}
        rows={p.moves.map((m) => ({
          id: m.old_path,
          cells: [
            <PlanLines
              key="from"
              primary={<b>{base(m.old_path)}</b>}
              secondary={dir(m.old_path).replace(/\/$/, "")}
            />,
            <PlanLines
              key="to"
              primary={dir(m.path)}
              secondary={
                base(m.old_path) !== base(m.path)
                  ? moves.as(base(m.path))
                  : undefined
              }
            />,
          ],
        }))}
      />
      {stays.length > 0 && (
        <Note kind="leftOut" fact={moves.staysFact(stays.length)}>
          {stays
            .map((st) => moves.staysValue(base(st.path), st.reason))
            .join(line.summaryJoin)}
        </Note>
      )}
    </div>
  );
}

function LinksTable({ plan: p }: { plan: DocumentMoves }) {
  const mono = "font-(family-name:--font-mono) wrap-anywhere";
  return (
    <PlanTable
      headers={[moves.label.note, moves.label.linkNow, moves.label.afterMove]}
      columns={[30, 30, 40]}
      limit={LINK_LIMIT}
      rows={repairedLinks(p).map((l) => ({
        id: `${l.source_path}:${l.start}`,
        cells: [
          <PathChip key="note" path={l.source_path} />,
          <span key="now" className={mono}>
            {l.target_before}
          </span>,
          <span key="after" className={mono}>
            {l.replacement}
          </span>,
        ],
      }))}
    />
  );
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
