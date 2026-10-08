// File: components/component-elements/separator.tsx
//
import { Separator as SeparatorBase } from "../component-core/separator";
import { cn } from "../lib/utils";

import type { ComponentProps } from "react";

// Base UI emits data-orientation. Core data-horizontal/vertical selectors leave separator 0x0.
export function Separator({
  className,
  ...props
}: ComponentProps<typeof SeparatorBase>) {
  return (
    <SeparatorBase
      className={cn(
        "data-[orientation=horizontal]:h-px data-[orientation=horizontal]:w-full data-[orientation=vertical]:h-full data-[orientation=vertical]:w-px",
        className,
      )}
      {...props}
    />
  );
}
