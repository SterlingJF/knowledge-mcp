// K14 Tabs, the look: core's tab parts restyled. Underline on the active tab; the list rules off the panels.
// The data-driven tabs with counts are the K14 pattern in component-patterns/tabs.tsx.
import type { ComponentProps } from "react";

import {
  Tabs as CoreTabs,
  TabsContent as CoreTabsContent,
  TabsList as CoreTabsList,
  TabsTrigger as CoreTabsTrigger,
} from "@/component-core/tabs";
import { cn } from "@/lib/utils";

// Base UI sets data-orientation and data-active; the underline is a ::after on the active tab.
// The `!` overrides beat the core's group-variant selectors (focus ring, shadow, size).
const triggerClass = cn(
  "relative h-auto flex-none cursor-pointer rounded-none border-0 px-0 py-km-3 text-sm! leading-sm font-semibold text-muted-foreground! transition-none outline-none hover:text-foreground!",
  "data-active:bg-transparent! data-active:text-foreground! data-active:border-transparent!",
  "shadow-none! focus-visible:border-0 focus-visible:ring-0 focus-visible:outline-none focus-visible:shadow-km-focus-ring!",
  "after:absolute after:inset-x-0 after:bottom-0 after:h-km-underline after:bg-foreground after:opacity-0 after:transition-none data-[orientation=horizontal]:data-active:after:opacity-100 data-active:after:opacity-100!",
  "pointer-coarse:min-h-km-target",
);

export function Tabs({ className, ...props }: ComponentProps<typeof CoreTabs>) {
  return (
    <CoreTabs
      className={cn("flex-col gap-km-gap-group", className)}
      {...props}
    />
  );
}

export function TabsList({
  variant = "line",
  className,
  ...props
}: ComponentProps<typeof CoreTabsList>) {
  return (
    <CoreTabsList
      variant={variant}
      className={cn(
        "h-auto w-full justify-start gap-km-gap-group rounded-none border-b-hairline border-border p-0",
        className,
      )}
      {...props}
    />
  );
}

export function TabsTrigger({
  className,
  ...props
}: ComponentProps<typeof CoreTabsTrigger>) {
  return <CoreTabsTrigger className={cn(triggerClass, className)} {...props} />;
}

export function TabsContent(props: ComponentProps<typeof CoreTabsContent>) {
  return <CoreTabsContent {...props} />;
}
