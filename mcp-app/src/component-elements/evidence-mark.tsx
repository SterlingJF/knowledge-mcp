// K03 Evidence mark: how well the sources back a proposed change. Neutral tone; a mark is not a status.
import { ArrowRightLeft, CircleCheck, CircleDashed, GitFork } from "lucide-react";
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
        "flex w-fit items-center gap-(--km-space-2) whitespace-nowrap rounded-(--border-radius-full) border-(length:--border-width-regular) border-(--color-border-tertiary) bg-(--color-background-primary) px-(--km-space-4) text-(length:--font-text-xs-size) leading-(--font-text-xs-line-height) font-(--font-weight-semibold) text-(--color-text-primary)",
        className,
      )}
    >
      <Icon aria-hidden className="size-(--km-space-5) shrink-0" />
      {evidence[mark]}
    </span>
  );
}
