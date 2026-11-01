// Gallery-only stand-in for Claude's inline frame (prefersBorder), so stories read like the frames.
import type { ReactNode } from "react";

import { PathChip } from "@/component-elements/chips";
import { meta } from "@/copy/en";

export function HarnessFrame({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-xl border-hairline border-dashed border-input p-km-6">
      {children}
    </div>
  );
}

/** The example meta line from the frames: the file chip, then the type and reader. */
export const exampleMeta = (
  <>
    <PathChip path="cache-proposal.md" />
    <span>Design proposal{meta.join}for maintainers</span>
  </>
);
