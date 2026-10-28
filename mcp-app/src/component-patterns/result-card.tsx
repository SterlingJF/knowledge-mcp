// P05 Result and refusal. A result says what was done, when and by whom, with Undo and one other
// step. A refusal says why and that nothing changed, with one next step.
import type { ReactNode } from "react";

import { Note } from "@/component-elements/note";
import { action as actionCopy, frozen, line } from "@/copy/en";
import { CardShell } from "./card-shell";
import type { CardAction } from "./card-shell";
import type { CardLifecycle } from "./card-lifecycle";

type Common = {
  eyebrow: ReactNode;
  title: ReactNode;
  /** A label from `badge.done` or `badge.refused`. */
  badgeLabel: ReactNode;
  children?: ReactNode;
  why?: ReactNode;
  lifecycle: CardLifecycle;
  flat?: boolean;
};

export type ResultCardProps =
  | (Common & {
      kind: "result";
      what: string;
      when: string;
      who: string;
      /** The message Undo sends. */
      undoMessage: string;
      secondary?: CardAction;
    })
  | (Common & {
      kind: "refusal";
      /** Why it was refused, and that nothing changed. */
      reason: ReactNode;
      nextStep: CardAction;
    });

export function ResultCard(props: ResultCardProps) {
  const { eyebrow, title, badgeLabel, children, why, lifecycle, flat } = props;
  if (props.kind === "result") {
    const actions: CardAction[] = [
      {
        label: actionCopy.undo,
        message: props.undoMessage,
        frozenLine: frozen.undoRequested,
      },
    ];
    if (props.secondary) actions.push(props.secondary);
    return (
      <CardShell
        eyebrow={eyebrow}
        title={title}
        meta={[props.what, props.when, props.who].join(line.summaryJoin)}
        badge={{ tone: "done", label: badgeLabel }}
        why={why}
        actions={actions}
        onAction={lifecycle.press}
        state={lifecycle.state}
        frozenLine={lifecycle.frozenLine}
        flat={flat}
      >
        {children}
      </CardShell>
    );
  }
  return (
    <CardShell
      eyebrow={eyebrow}
      title={title}
      badge={{ tone: "refused", label: badgeLabel }}
      why={why}
      actions={[props.nextStep]}
      onAction={lifecycle.press}
      state={lifecycle.state}
      frozenLine={lifecycle.frozenLine}
      flat={flat}
    >
      <Note kind="warning" className="mt-[var(--km-space-5)]">
        {props.reason}
      </Note>
      {children}
    </CardShell>
  );
}
