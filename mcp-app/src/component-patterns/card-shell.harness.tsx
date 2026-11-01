// Gallery-only stand-in for Claude's inline frame (prefersBorder), 760px wide like the chat column, so stories read like the frames.
import type { ReactNode } from "react";

import { PathChip } from "@/component-elements/chips";
import { meta } from "@/copy/en";

export function HarnessFrame({ children }: { children: ReactNode }) {
  return (
    <div className="w-190 max-w-full rounded-xl border border-dashed border-input p-4">
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
