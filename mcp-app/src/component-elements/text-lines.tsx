// K07 Text lines: the fixed text roles inside a card. Three sizes (xs, sm, heading-md) and two weights (normal, semibold) only (F02).
import type { ComponentProps, ReactNode } from "react";

import { cn } from "@/lib/utils";

const xs = "text-xs leading-xs";
const tertiary = "text-muted-foreground";

type LineProps = ComponentProps<"div">;

export function Eyebrow({ className, ...props }: LineProps) {
  return (
    <div
      className={cn(
        xs,
        tertiary,
        "font-semibold uppercase tracking-[0.07em]",
        className,
      )}
      {...props}
    />
  );
}

export function Title({ className, ...props }: LineProps) {
  return (
    <div
      className={cn(
        "mt-km-gap-tight font-semibold text-base leading-base",
        className,
      )}
      {...props}
    />
  );
}

export function Meta({ className, ...props }: LineProps) {
  return (
    <div
      className={cn(
        xs,
        tertiary,
        "mt-km-gap-inline flex flex-wrap items-center gap-x-km-gap-inline gap-y-km-gap-tight",
        className,
      )}
      {...props}
    />
  );
}

export function WhyLine({ className, ...props }: LineProps) {
  return (
    <div
      className={cn(xs, tertiary, "mt-km-gap-group", className)}
      {...props}
    />
  );
}

export function FrozenLine({ className, ...props }: LineProps) {
  return (
    <div
      className={cn(xs, tertiary, "mt-km-gap-group", className)}
      {...props}
    />
  );
}

export function CurrentText({
  label,
  children,
  className,
  ...props
}: Omit<ComponentProps<"span">, "children"> & {
  label: ReactNode;
  children: ReactNode;
}) {
  return (
    <span className={className} {...props}>
      <span className="font-semibold">{label}:</span>{" "}
      <span className={tertiary}>{children}</span>
    </span>
  );
}
