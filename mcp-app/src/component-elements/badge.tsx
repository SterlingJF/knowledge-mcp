import type { ReactNode } from "react";
import { Check, TriangleAlert } from "lucide-react";

import { Badge as CoreBadge } from "@/component-core/badge";
import { cn } from "@/lib/utils";

export type BadgeTone = "waiting" | "done" | "refused" | "working" | "neutral";

const toneClass: Record<BadgeTone, string> = {
  waiting:
    "bg-[var(--color-background-warning)] text-[var(--color-text-warning)]",
  done: "bg-[var(--color-background-success)] text-[var(--color-text-success)]",
  refused:
    "bg-[var(--color-background-danger)] text-[var(--color-text-danger)]",
  working: "bg-[var(--color-background-info)] text-[var(--color-text-info)]",
  neutral:
    "bg-[var(--color-background-secondary)] text-[var(--color-text-tertiary)]",
};

/** Waiting on the person: a dot whose ring pulses; static when motion is reduced. */
function PulseDot() {
  return (
    <span
      aria-hidden="true"
      data-testid="pulse-dot"
      className="relative size-[var(--km-dot)] flex-none rounded-full bg-current after:absolute after:inset-0 after:rounded-full after:bg-current after:content-[''] after:[animation:km-pulse_var(--km-pulse)] motion-reduce:after:animate-none"
    />
  );
}

export type BadgeProps = {
  tone: BadgeTone;
  /** A label from `badge` in src/copy/en.ts. */
  children: ReactNode;
  className?: string;
};

export function Badge({ tone, children, className }: BadgeProps) {
  return (
    <CoreBadge
      data-tone={tone}
      className={cn(
        "h-auto gap-[var(--km-space-2)] rounded-[var(--border-radius-full)] border-0 px-[var(--km-space-4)] py-[var(--km-space-1)] text-[length:var(--font-text-xs-size)] leading-[var(--font-text-xs-line-height)] font-[var(--font-weight-semibold)] [&>svg]:size-[var(--km-icon)]!",
        toneClass[tone],
        className,
      )}
    >
      {tone === "waiting" && <PulseDot />}
      {tone === "done" && <Check aria-hidden="true" data-icon="done" />}
      {tone === "refused" && (
        <TriangleAlert aria-hidden="true" data-icon="refused" />
      )}
      {children}
    </CoreBadge>
  );
}
