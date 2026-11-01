// Link button: an underlined text control that sends nothing ("Show why", "Show the change").
// On touch its hit area grows to 44pt invisibly, so the line it sits in keeps its height.
import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

export function LinkButton({
  className,
  type = "button",
  ...props
}: ComponentProps<"button">) {
  return (
    <button
      type={type}
      className={cn(
        "relative inline-flex cursor-pointer items-center gap-km-2 rounded-xs border-0 bg-transparent p-0 text-xs leading-xs text-foreground underline underline-offset-2 outline-none focus-visible:shadow-km-focus-ring pointer-coarse:before:absolute pointer-coarse:before:top-1/2 pointer-coarse:before:left-1/2 pointer-coarse:before:h-km-target pointer-coarse:before:w-full pointer-coarse:before:min-w-km-target pointer-coarse:before:-translate-1/2 pointer-coarse:before:content-['']",
        className,
      )}
      {...props}
    />
  );
}
