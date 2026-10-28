// P07 Full view: the same card, flat inside Claude's fullscreen chrome, with every detail and
// the same two actions. A press also returns to the inline card.
import type { ReactNode } from "react";

import { useCardHost } from "@/bridge/bridge";
import type { BadgeTone } from "@/component-elements/badge";
import { CardShell } from "./card-shell";
import type { CardAction } from "./card-shell";
import type { CardLifecycle } from "./card-lifecycle";

export type FullViewProps = {
  eyebrow: ReactNode;
  title: ReactNode;
  meta?: ReactNode;
  badge?: { tone: BadgeTone; label: ReactNode };
  children: ReactNode;
  why?: ReactNode;
  actions: readonly CardAction[];
  lifecycle: CardLifecycle;
};

export function FullView({
  children,
  actions,
  lifecycle,
  ...shell
}: FullViewProps) {
  const host = useCardHost();
  return (
    <CardShell
      {...shell}
      flat
      state={lifecycle.state}
      frozenLine={lifecycle.frozenLine}
      actions={actions}
      onAction={(item) => {
        lifecycle.press(item);
        void host.requestInline();
      }}
    >
      {children}
    </CardShell>
  );
}
