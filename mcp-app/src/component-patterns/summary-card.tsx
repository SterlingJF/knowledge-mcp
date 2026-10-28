// P07 Summary: the inline card. At most five data points, two actions, and Full view when the
// host offers it.
import type { ReactNode } from "react";

import { useCardHost } from "@/bridge/bridge";
import type { BadgeTone } from "@/component-elements/badge";
import { KeyValue } from "@/component-elements/key-value";
import type { KeyValueRow } from "@/component-elements/key-value";
import { CardShell } from "./card-shell";
import type { CardAction } from "./card-shell";
import { lifecycleProps } from "./card-lifecycle";
import type { CardLifecycle } from "./card-lifecycle";

export type SummaryCardProps = {
  eyebrow: ReactNode;
  title: ReactNode;
  meta?: ReactNode;
  badge?: { tone: BadgeTone; label: ReactNode };
  rows: readonly KeyValueRow[];
  children?: ReactNode;
  why?: ReactNode;
  actions: readonly CardAction[];
  /** From useCardLifecycle, held by the card so it survives the switch to the full view. */
  lifecycle: CardLifecycle;
};

export function SummaryCard({
  rows,
  children,
  actions,
  lifecycle,
  ...shell
}: SummaryCardProps) {
  const host = useCardHost();
  return (
    <CardShell
      {...shell}
      {...lifecycleProps(lifecycle)}
      actions={actions}
      onFullView={
        host.canFullView ? () => void host.requestFullView() : undefined
      }
    >
      <KeyValue rows={rows} />
      {children}
    </CardShell>
  );
}
