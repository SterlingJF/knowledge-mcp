// K03 Evidence mark: how well the sources back a proposed change. An icon and a word in the muted tone,
// with no box, so it reads as a note on the change and never as a second status badge.
import {
  ArrowRightLeft,
  CircleCheck,
  CircleDashed,
  GitFork,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { evidence } from "@/copy/en";
import { cn } from "@/lib/utils";

/** The proposal schema's `mark` values. */
export type EvidenceKind = keyof typeof evidence;

const icons: Record<EvidenceKind, LucideIcon> = {
  supported: CircleCheck,
  partly: CircleDashed,
  conflicting: ArrowRightLeft,
  suggested: GitFork,
};

export function EvidenceMark({
  mark,
  className,
}: {
  mark: EvidenceKind;
  className?: string;
}) {
  const Icon = icons[mark];
  return (
    <span
      data-mark={mark}
      className={cn(
        "inline-flex w-fit items-center gap-1 text-xs whitespace-nowrap text-muted-foreground",
        className,
      )}
    >
      <Icon aria-hidden className="size-3 shrink-0" />
      {evidence[mark]}
    </span>
  );
}
