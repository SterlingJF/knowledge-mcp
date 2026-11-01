// P01 Card shell: the eyebrow, title, meta and badge; the body; the why line; at most two actions.
// It places the flat core Card: Claude draws the frame inline (prefersBorder) and its chrome in the full view.
import type { ReactNode } from "react";
import { ChevronDown, Maximize2 } from "lucide-react";

import { Button } from "@/component-core/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/component-core/collapsible";
import { Badge } from "@/component-elements/badge";
import type { BadgeTone } from "@/component-elements/badge";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/component-elements/card";
import { Caption, Eyebrow } from "@/component-elements/text-lines";
import {
  action as actionCopy,
  badge as badgeCopy,
  frozen as frozenCopy,
} from "@/copy/en";

export const MAX_CARD_ACTIONS = 2;

export type CardState = "live" | "frozen" | "replaced";

export type CardAction = {
  label: string;
  /** The exact text the press sends as the person's message. */
  message: string;
  /** The line from `frozen` in src/copy/en.ts shown once this action was pressed. */
  frozenLine: string;
  /** Defaults to ghost, the decline look; the first action is usually default, the one filled button. */
  variant?: "default" | "outline" | "ghost";
  icon?: ReactNode;
  /** Shown but not pressable, e.g. Save with no change kept. */
  disabled?: boolean;
  /** Model context sent with the message, unseen by the person (e.g. a preview's digest). */
  context?: Record<string, unknown>;
};

/**
 * A show/hide control in the action row (R01/R02 "Show the change"): a core Collapsible whose panel is
 * the card's body. It sends nothing, never freezes the card and is not one of the two actions.
 * Hidden once the card is frozen or replaced.
 */
export type CardDisclosure = {
  label: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
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
  disclosure?: CardDisclosure;
  state?: CardState;
  /** Shown when frozen. */
  frozenLine?: ReactNode;
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
  disclosure,
  state = "live",
  frozenLine,
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
  const showActions = live && (actions.length > 0 || disclosure);
  const cardProps = {
    "data-state": state,
    className,
  };
  const content = (
    <>
      <CardHeader>
        {/* One block in the first column, so the action never takes a line of it. */}
        <div className="flex min-w-0 flex-col gap-1">
          <Eyebrow>{eyebrow}</Eyebrow>
          <CardTitle>{title}</CardTitle>
          {meta != null && <CardDescription>{meta}</CardDescription>}
        </div>
        {(shownBadge || (onFullView && live)) && (
          <CardAction>
            {shownBadge && (
              <Badge tone={shownBadge.tone}>{shownBadge.label}</Badge>
            )}
            {onFullView && live && (
              <Button variant="outline" size="xs" onClick={onFullView}>
                <Maximize2 aria-hidden="true" data-icon="inline-start" />
                {actionCopy.fullView}
              </Button>
            )}
          </CardAction>
        )}
      </CardHeader>
      {children != null &&
        (disclosure ? (
          <CollapsibleContent render={<CardContent />}>
            {children}
          </CollapsibleContent>
        ) : (
          <CardContent>{children}</CardContent>
        ))}
      {((live && why != null) ||
        showActions ||
        (!live && shownFrozen != null)) && (
        <CardFooter>
          {live && why != null && <Caption>{why}</Caption>}
          {showActions && (
            <div className="flex flex-wrap items-center gap-2">
              {actions.map((item) => (
                <Button
                  key={item.label}
                  variant={item.variant ?? "ghost"}
                  disabled={item.disabled}
                  onClick={() => onAction?.(item)}
                >
                  {item.icon}
                  {item.label}
                </Button>
              ))}
              {disclosure && live && (
                <CollapsibleTrigger render={<Button variant="ghost" />}>
                  {disclosure.label}
                  <ChevronDown
                    aria-hidden="true"
                    data-icon="inline-end"
                    className="transition-transform group-data-panel-open/button:rotate-180"
                  />
                </CollapsibleTrigger>
              )}
            </div>
          )}
          {!live && shownFrozen != null && <Caption>{shownFrozen}</Caption>}
        </CardFooter>
      )}
    </>
  );
  if (!disclosure) return <Card {...cardProps}>{content}</Card>;
  return (
    <Collapsible
      open={disclosure.open}
      onOpenChange={disclosure.onOpenChange}
      render={<Card {...cardProps} />}
    >
      {content}
    </Collapsible>
  );
}
