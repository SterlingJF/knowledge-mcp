// K14 Tabs: switch between views of one card in the full view (M02). Underline on the active tab, a count after the label.
// Places the K14 element's parts from data; the look is in component-elements/tabs.tsx.
import type { ReactNode } from "react";

import {
  Tabs as TabsRoot,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/component-elements/tabs";
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
    <TabsRoot
      value={value}
      defaultValue={defaultValue ?? tabs[0]?.value}
      onValueChange={(v) => onValueChange?.(String(v))}
      className={className}
    >
      <TabsList>
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
