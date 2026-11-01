import type { ComponentProps, ReactNode } from "react";

import { Button as CoreButton } from "@/component-core/button";
import { cn } from "@/lib/utils";

export type ButtonVariant = "primary" | "secondary" | "ghost";

const variantClass: Record<ButtonVariant, string> = {
  primary:
    "border-inverse bg-inverse text-inverse hover:bg-inverse hover:opacity-km-hover",
  secondary: "border-border bg-secondary text-foreground hover:bg-muted",
  ghost: "border-transparent bg-transparent text-foreground hover:bg-muted",
};

/** Shared look of every km button: tokens only, visible focus ring, 44pt on touch. */
export const kmButtonBase =
  "h-auto gap-km-3 rounded-md border-hairline border-solid px-km-5 py-km-3 text-sm leading-sm font-semibold focus-visible:border-ring focus-visible:ring-0 focus-visible:shadow-km-focus-ring disabled:opacity-km-disabled pointer-coarse:min-h-km-target [&_svg:not([class*='size-'])]:size-km-icon";

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
