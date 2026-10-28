// P05 Result and refusal. A result says what was done, when and by whom, with Undo and one other
// step. A refusal says why and that nothing changed, with one next step.
import type { ReactNode } from "react";
import { Undo2 } from "lucide-react";

import { Note } from "@/component-elements/note";
import { action as actionCopy, frozen, line, meta } from "@/copy/en";
import { CardShell } from "./card-shell";
import type { CardAction } from "./card-shell";
import { lifecycleProps } from "./card-lifecycle";
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
      /** When it was recorded: `Oct 28, 09:41`. */
      when: string;
      /** Whose OK; defaults to `meta.approvedByYou`. */
      who?: string;
      /** The message Undo sends. */
      undoMessage: string;
      secondary?: CardAction;
    })
  | (Common & {
      kind: "refusal";
      /** Why it was refused; the card adds that nothing was changed. */
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
        variant: "secondary",
        icon: <Undo2 aria-hidden="true" />,
      },
    ];
    if (props.secondary) actions.push(props.secondary);
    return (
      <CardShell
        eyebrow={eyebrow}
        title={title}
        meta={
          meta.recorded(props.when) +
          meta.join +
          (props.who ?? meta.approvedByYou)
        }
        badge={{ tone: "done", label: badgeLabel }}
        why={why}
        actions={actions}
        {...lifecycleProps(lifecycle)}
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
      {...lifecycleProps(lifecycle)}
      flat={flat}
    >
      <Note kind="warning" className="mt-[var(--km-gap-group)]">
        {props.reason} {line.nothingChanged}
      </Note>
      {children}
    </CardShell>
  );
}
