// P01 Card shell: eyebrow, title, meta and badge; the body; the why line; at most two actions.
// The card paints no background, border or padding: Claude draws the frame inline (prefersBorder)
// and its fullscreen chrome in the full view, so inline and flat differ only in context.
import type { ReactNode } from "react";

import { Badge } from "@/component-elements/badge";
import type { BadgeTone } from "@/component-elements/badge";
import { Button } from "@/component-elements/button";
import type { ButtonVariant } from "@/component-elements/button";
import { FullViewButton } from "@/component-elements/full-view-button";
import {
  Eyebrow,
  FrozenLine,
  Meta,
  Title,
  WhyLine,
} from "@/component-elements/text-lines";
import { badge as badgeCopy, frozen as frozenCopy } from "@/copy/en";
import { cn } from "@/lib/utils";

export const MAX_CARD_ACTIONS = 2;

export type CardState = "live" | "frozen" | "replaced";

export type CardAction = {
  label: string;
  /** The exact text the press sends as the person's message. */
  message: string;
  /** The line from `frozen` in src/copy/en.ts shown once this action was pressed. */
  frozenLine: string;
  /** Defaults to ghost, the decline look; the first action is usually primary. */
  variant?: ButtonVariant;
  icon?: ReactNode;
};

export type CardShellProps = {
  eyebrow: ReactNode;
  title: ReactNode;
  meta?: ReactNode;
  badge?: { tone: BadgeTone; label: ReactNode };
  /** Shows the Full view button in the header. */
  onFullView?: () => void;
  children?: ReactNode;
  why?: ReactNode;
  actions?: readonly CardAction[];
  onAction?: (action: CardAction) => void;
  state?: CardState;
  /** Shown when frozen. */
  frozenLine?: ReactNode;
  flat?: boolean;
  className?: string;
};

export function CardShell({
  eyebrow,
  title,
  meta,
  badge,
  onFullView,
  children,
  why,
  actions = [],
  onAction,
  state = "live",
  frozenLine,
  flat = false,
  className,
}: CardShellProps) {
  if (actions.length > MAX_CARD_ACTIONS) {
    throw new Error(
      `A card has at most ${MAX_CARD_ACTIONS} actions; got ${actions.length}.`,
    );
  }
  const live = state === "live";
  const shownBadge =
    state === "replaced"
      ? { tone: "neutral" as const, label: badgeCopy.neutral.replaced }
      : badge;
  const shownFrozen = state === "replaced" ? frozenCopy.replaced : frozenLine;
  return (
    <section
      data-state={state}
      data-flat={flat || undefined}
      className={cn(
        "@container border-0 bg-transparent p-0 text-[color:var(--color-text-primary)]",
        className,
      )}
    >
      {/* Narrow: badge and Full view drop below the title. Wide: they sit at its right. */}
      <header className="flex flex-col items-start gap-[var(--km-space-4)] @sm:flex-row @sm:justify-between @sm:gap-[var(--km-space-5)]">
        <div className="min-w-0">
          <Eyebrow>{eyebrow}</Eyebrow>
          <Title>{title}</Title>
          {meta != null && <Meta>{meta}</Meta>}
        </div>
        {(shownBadge || (onFullView && live)) && (
          <span className="flex flex-none items-center gap-[var(--km-space-4)]">
            {shownBadge && (
              <Badge tone={shownBadge.tone}>{shownBadge.label}</Badge>
            )}
            {onFullView && live && (
              <FullViewButton onRequestFullView={onFullView} />
            )}
          </span>
        )}
      </header>
      {children}
      {live && why != null && <WhyLine>{why}</WhyLine>}
      {live && actions.length > 0 && (
        <div className="mt-[var(--km-space-5)] flex flex-wrap items-center gap-[var(--km-space-4)]">
          {actions.map((item) => (
            <Button
              key={item.label}
              variant={item.variant ?? "ghost"}
              icon={item.icon}
              onClick={() => onAction?.(item)}
            >
              {item.label}
            </Button>
          ))}
        </div>
      )}
      {!live && shownFrozen != null && <FrozenLine>{shownFrozen}</FrozenLine>}
    </section>
  );
}
