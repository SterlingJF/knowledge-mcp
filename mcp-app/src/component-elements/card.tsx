// The card: core Card, flat. Claude draws the frame inline (prefersBorder) and the chrome in the
// full view, so the card keeps shadcn's structure and gaps but paints no ring, ground or padding.
import type { ComponentProps } from "react";

import {
  Card as CoreCard,
  CardAction as CoreCardAction,
  CardContent as CoreCardContent,
  CardDescription as CoreCardDescription,
  CardFooter as CoreCardFooter,
  CardHeader as CoreCardHeader,
  CardTitle as CoreCardTitle,
} from "@/component-core/card";
import { cn } from "@/lib/utils";

export function Card({ className, ...props }: ComponentProps<typeof CoreCard>) {
  return (
    <CoreCard
      className={cn(
        "@container gap-4 overflow-visible rounded-none py-0 shadow-none ring-0",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({
  className,
  ...props
}: ComponentProps<typeof CoreCardHeader>) {
  return <CoreCardHeader className={cn("px-0", className)} {...props} />;
}

export function CardContent({
  className,
  ...props
}: ComponentProps<typeof CoreCardContent>) {
  return <CoreCardContent className={cn("px-0", className)} {...props} />;
}

export function CardFooter({
  className,
  ...props
}: ComponentProps<typeof CoreCardFooter>) {
  return (
    <CoreCardFooter
      className={cn("flex-col items-start gap-4 px-0", className)}
      {...props}
    />
  );
}

/** Badge and Full view, top right; under 448px of header they drop under the title instead of squeezing it. */
export function CardAction({
  className,
  ...props
}: ComponentProps<typeof CoreCardAction>) {
  return (
    <CoreCardAction
      className={cn(
        "flex items-center gap-2 @max-md/card-header:col-span-2 @max-md/card-header:col-start-1 @max-md/card-header:row-span-1 @max-md/card-header:row-start-auto @max-md/card-header:justify-self-start",
        className,
      )}
      {...props}
    />
  );
}

/** The heading, in Claude's emphasized weight. */
export function CardTitle({
  className,
  ...props
}: ComponentProps<typeof CoreCardTitle>) {
  return (
    <CoreCardTitle className={cn("font-semibold", className)} {...props} />
  );
}

/** The meta line under the title: small parts in a row that wraps. */
export function CardDescription({
  className,
  ...props
}: ComponentProps<typeof CoreCardDescription>) {
  return (
    <CoreCardDescription
      className={cn(
        "flex flex-wrap items-center gap-x-2 gap-y-1 text-xs",
        className,
      )}
      {...props}
    />
  );
}
