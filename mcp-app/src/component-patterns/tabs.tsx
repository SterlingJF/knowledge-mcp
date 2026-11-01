// K14 Tabs: switch between views of one card in the full view (M02). Core Tabs, line variant, a count after the label.
import type { ReactNode } from "react";

import {
  Tabs as TabsRoot,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/component-core/tabs";
import { label as labels } from "@/copy/en";

export type TabItem = {
  value: string;
  label: string;
  /** Shown after the label: `Moves (3)`. */
  count?: number;
  content: ReactNode;
};

export function Tabs({
  tabs,
  defaultValue,
  className,
}: {
  tabs: TabItem[];
  defaultValue?: string;
  className?: string;
}) {
  return (
    <TabsRoot
      defaultValue={defaultValue ?? tabs[0]?.value}
      className={className}
    >
      <TabsList variant="line">
        {tabs.map((tab) => (
          <TabsTrigger key={tab.value} value={tab.value}>
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
    </TabsRoot>
  );
}
