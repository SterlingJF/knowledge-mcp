// K07 Text lines: the text roles the card's core parts don't name. Title and meta are core CardTitle and
// CardDescription; these are the eyebrow over the title, the caption under the body, and a change's current text.
import type { ComponentProps, ReactNode } from "react";

import { cn } from "@/lib/utils";

type LineProps = ComponentProps<"div">;

/** What kind of card this is, above its title: `Proposed changes`. */
export function Eyebrow({ className, ...props }: LineProps) {
  return (
    <div
      className={cn(
        "text-xs font-semibold tracking-wide text-muted-foreground uppercase",
        className,
      )}
      {...props}
    />
  );
}

/** A quiet line under the body: why the card waits, or what a press did. */
export function Caption({ className, ...props }: LineProps) {
  return (
    <div
      className={cn("text-xs text-muted-foreground", className)}
      {...props}
    />
  );
}

export function CurrentText({
  label,
  children,
  struck = false,
  className,
  ...props
}: Omit<ComponentProps<"span">, "children"> & {
  label: ReactNode;
  children: ReactNode;
  /** Left out: the text is struck through. */
  struck?: boolean;
}) {
  return (
    <span className={cn(struck && "line-through", className)} {...props}>
      <span className="font-semibold">{label}:</span>{" "}
      <span className="text-muted-foreground">{children}</span>
    </span>
  );
}
