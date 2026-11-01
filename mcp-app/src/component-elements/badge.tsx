// K01 Status badge: core Badge in the host's status colours. Waiting carries a pulsing dot, done a check,
// refused a warning sign, so the state never rests on colour alone.
import type { ReactNode } from "react";
import { Check, TriangleAlert } from "lucide-react";

import { Badge as CoreBadge } from "@/component-core/badge";
import { cn } from "@/lib/utils";

export type BadgeTone = "waiting" | "done" | "refused" | "neutral";

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
      variant={
        tone === "refused"
          ? "destructive"
          : tone === "neutral"
            ? "outline"
            : "default"
      }
      className={cn(
        tone === "waiting" && "bg-warning text-warning-foreground",
        tone === "done" && "bg-success text-success-foreground",
        className,
      )}
    >
      {tone === "waiting" && (
        <span
          aria-hidden="true"
          data-testid="pulse-dot"
          className="size-1.5 rounded-full bg-current motion-safe:animate-pulse"
        />
      )}
      {tone === "done" && <Check aria-hidden="true" data-icon="inline-start" />}
      {tone === "refused" && (
        <TriangleAlert aria-hidden="true" data-icon="inline-start" />
      )}
      {children}
    </CoreBadge>
  );
}
