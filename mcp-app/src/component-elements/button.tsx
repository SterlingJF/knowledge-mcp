import type { ComponentProps, ReactNode } from "react";

import { Button as CoreButton } from "@/component-core/button";
import { cn } from "@/lib/utils";

export type ButtonVariant = "primary" | "secondary" | "ghost";

const variantClass: Record<ButtonVariant, string> = {
  primary:
    "border-[var(--color-background-inverse)] bg-[var(--color-background-inverse)] text-[var(--color-text-inverse)] hover:bg-[var(--color-background-inverse)] hover:opacity-88",
  secondary:
    "border-[var(--color-border-tertiary)] bg-[var(--color-background-primary)] text-[var(--color-text-primary)] hover:bg-[var(--color-background-secondary)]",
  ghost:
    "border-transparent bg-transparent text-[var(--color-text-primary)] hover:bg-[var(--color-background-secondary)]",
};

/** Shared look of every km button: tokens only, visible focus ring, 44pt on touch. */
export const kmButtonBase =
  "h-auto gap-[var(--km-space-3)] rounded-[var(--border-radius-md)] border-[length:var(--border-width-regular)] border-solid px-[var(--km-space-5)] py-[var(--km-space-3)] text-[length:var(--font-text-sm-size)] leading-[var(--font-text-sm-line-height)] font-[var(--font-weight-semibold)] focus-visible:border-[var(--color-ring-primary)] focus-visible:ring-0 focus-visible:shadow-[0_0_0_2px_var(--color-background-primary),0_0_0_4px_var(--color-ring-primary)] disabled:opacity-40 pointer-coarse:min-h-[var(--km-target)] [&_svg:not([class*='size-'])]:size-[var(--km-icon)]";

export type ButtonProps = Omit<
  ComponentProps<typeof CoreButton>,
  "variant" | "size" | "children"
> & {
  variant?: ButtonVariant;
  icon?: ReactNode;
  children: ReactNode;
};

export function Button({
  variant = "secondary",
  icon,
  children,
  className,
  ...props
}: ButtonProps) {
  return (
    <CoreButton
      data-variant={variant}
      className={cn(kmButtonBase, variantClass[variant], className)}
      {...props}
    >
      {icon}
      {children}
    </CoreButton>
  );
}
