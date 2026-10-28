// P07 Full view: the same card, flat inside Claude's fullscreen chrome, with every detail and
// the same two actions. A press also returns to the inline card.
import type { ReactNode } from "react";

import { useCardHost } from "@/bridge/bridge";
import type { BadgeTone } from "@/component-elements/badge";
import { CardShell } from "./card-shell";
import type { CardAction } from "./card-shell";
import { lifecycleProps } from "./card-lifecycle";
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
      {...lifecycleProps(lifecycle)}
      actions={actions}
      onAction={(item) => {
        lifecycle.press(item);
        void host.requestInline();
      }}
    >
      {/* The body: one group gap after the header and between its parts (E02F). */}
      <div className="mt-(--km-gap-group) flex flex-col gap-(--km-gap-group)">
        {children}
      </div>
    </CardShell>
  );
}
