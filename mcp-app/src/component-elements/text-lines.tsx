// K07 Text lines: the fixed text roles inside a card. Three sizes (xs, sm, heading-md) and two weights (normal, semibold) only (F02).
import type { ComponentProps, ReactNode } from "react";

import { cn } from "@/lib/utils";

const xs =
  "text-[length:var(--font-text-xs-size)] leading-[var(--font-text-xs-line-height)]";
const tertiary = "text-[color:var(--color-text-tertiary)]";

type LineProps = ComponentProps<"div">;

export function Eyebrow({ className, ...props }: LineProps) {
  return (
    <div
      className={cn(
        xs,
        tertiary,
        "font-[weight:var(--font-weight-semibold)] uppercase tracking-[0.07em]",
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
        "mt-[var(--km-space-1)] font-[weight:var(--font-weight-semibold)] text-[length:var(--font-heading-md-size)] leading-[var(--font-heading-md-line-height)]",
        className,
      )}
      {...props}
    />
  );
}

export function Meta({ className, ...props }: LineProps) {
  return (
    <div
      className={cn(xs, tertiary, "mt-[var(--km-space-1)]", className)}
      {...props}
    />
  );
}

export function WhyLine({ className, ...props }: LineProps) {
  return (
    <div
      className={cn(xs, tertiary, "mt-[var(--km-space-5)]", className)}
      {...props}
    />
  );
}

export function FrozenLine({ className, ...props }: LineProps) {
  return (
    <div
      className={cn(xs, tertiary, "mt-[var(--km-space-5)]", className)}
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
      <span className="font-[weight:var(--font-weight-semibold)]">{label}:</span>{" "}
      <span className={tertiary}>{children}</span>
    </span>
  );
}
