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

export function FullView(props: FullViewProps) {
  const host = useCardHost();
  return (
    <FullViewLayout {...props} onPressed={() => void host.requestInline()} />
  );
}

/** The full view without the bridge: the gallery and tests draw it directly. */
export function FullViewLayout({
  children,
  actions,
  lifecycle,
  onPressed,
  ...shell
}: FullViewProps & { onPressed?: () => void }) {
  return (
    <CardShell
      {...shell}
      flat
      state={lifecycle.state}
      frozenLine={lifecycle.frozenLine}
      actions={actions}
      onAction={(item) => {
        lifecycle.press(item);
        onPressed?.();
      }}
    >
      {children}
    </CardShell>
  );
}
