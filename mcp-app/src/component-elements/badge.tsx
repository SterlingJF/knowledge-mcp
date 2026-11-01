import type { ReactNode } from "react";
import { Check, TriangleAlert } from "lucide-react";

import { Badge as CoreBadge } from "@/component-core/badge";
import { cn } from "@/lib/utils";

export type BadgeTone = "waiting" | "done" | "refused" | "neutral";

const toneClass: Record<BadgeTone, string> = {
  waiting: "bg-warning text-warning",
  done: "bg-success text-success",
  refused: "bg-danger text-destructive",
  neutral: "bg-muted text-secondary",
};

/** Waiting on the person: a dot whose ring pulses; static when motion is reduced. */
function PulseDot() {
  return (
    <span
      aria-hidden="true"
      data-testid="pulse-dot"
      className="relative size-km-dot flex-none rounded-full bg-current after:absolute after:inset-0 after:rounded-full after:bg-current after:content-[''] after:animate-km-pulse motion-reduce:after:animate-none"
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
        "h-auto gap-km-2 rounded-full border-0 px-km-4 py-km-1 text-xs leading-xs font-semibold [&>svg]:size-km-icon!",
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
