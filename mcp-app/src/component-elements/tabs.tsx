// K14 Tabs: switch between views of one card in the full view (M02). Underline on the active tab, a count after the label.
import type { ReactNode } from "react";

import {
  Tabs as CoreTabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/component-core/tabs";
import { label as labels } from "@/copy/en";
import { cn } from "@/lib/utils";

export type TabItem = {
  value: string;
  label: string;
  /** Shown after the label: `Moves (3)`. */
  count?: number;
  content: ReactNode;
};

export function Tabs({
  tabs,
  value,
  defaultValue,
  onValueChange,
  className,
}: {
  tabs: TabItem[];
  /** Controlled value; omit to let the tabs keep their own. */
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  className?: string;
}) {
  return (
    <CoreTabs
      value={value}
      defaultValue={defaultValue ?? tabs[0]?.value}
      onValueChange={(v) => onValueChange?.(String(v))}
      className={cn("gap-(--km-space-5)", className)}
    >
      <TabsList
        variant="line"
        className="h-auto w-full justify-start gap-(--km-space-5) rounded-none border-b-(length:--border-width-regular) border-(--color-border-tertiary) p-0 group-data-horizontal/tabs:h-auto"
      >
        {tabs.map((tab) => (
          <TabsTrigger
            key={tab.value}
            value={tab.value}
            className="h-auto flex-none cursor-pointer rounded-none border-0 px-0 py-(--km-space-3) text-(length:--font-text-xs-size) leading-(--font-text-xs-line-height) font-(--font-weight-semibold) text-(--color-text-tertiary) shadow-none transition-none outline-none hover:text-(--color-text-primary) focus-visible:border-0 focus-visible:ring-0 focus-visible:outline-none focus-visible:shadow-(--km-focus-ring) data-active:bg-transparent data-active:text-(--color-text-primary) dark:data-active:bg-transparent dark:data-active:text-(--color-text-primary) dark:text-(--color-text-tertiary) after:bg-(--color-text-primary) after:transition-none group-data-horizontal/tabs:after:bottom-0 group-data-horizontal/tabs:after:h-(--km-space-1) pointer-coarse:min-h-(--km-target)"
          >
            {tab.count == null
              ? tab.label
              : labels.withCount(tab.label, tab.count)}
          </TabsTrigger>
        ))}
      </TabsList>
      {tabs.map((tab) => (
        <TabsContent key={tab.value} value={tab.value}>
          {tab.content}
        </TabsContent>
      ))}
    </CoreTabs>
  );
}
