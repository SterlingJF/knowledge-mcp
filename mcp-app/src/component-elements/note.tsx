// K06 Note: a quiet block for something you should know before deciding. Bold the fact, then the reason.
import { Ban, Info, TriangleAlert } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { PathChip } from "@/component-elements/chips";
import { cn } from "@/lib/utils";

export type NoteKind = "info" | "leftOut" | "warning";

const icons: Record<NoteKind, LucideIcon> = {
  info: Info,
  leftOut: Ban,
  warning: TriangleAlert,
};

export function Note({
  kind,
  fact,
  children,
  className,
}: {
  kind: NoteKind;
  fact?: ReactNode;
  children?: ReactNode;
  className?: string;
}) {
  const Icon = icons[kind];
  return (
    <div
      role={kind === "warning" ? "alert" : "note"}
      data-kind={kind}
      className={cn(
        "flex items-start gap-(--km-space-4) rounded-(--border-radius-lg) bg-(--color-background-secondary) px-(--km-space-5) py-(--km-space-4) text-(length:--font-text-xs-size) leading-(--font-text-xs-line-height) text-(--color-text-primary)",
        className,
      )}
    >
      <Icon aria-hidden className="mt-(--km-space-1) size-(--km-space-5) shrink-0" />
      <div className="min-w-0">
        {fact != null && (
          <b className="font-(--font-weight-semibold)">{fact}</b>
        )}
        {fact != null && children != null && " "}
        {children}
      </div>
    </div>
  );
}

export type LeftOutFile = { file: string; reason: ReactNode };

/** Left-out files: chip and reason in a shared two-column grid, so the reasons align. */
export function LeftOutList({
  files,
  className,
}: {
  files: ReadonlyArray<LeftOutFile>;
  className?: string;
}) {
  return (
    <ul
      className={cn(
        "m-0 mt-(--km-space-4) grid list-none grid-cols-[max-content_1fr] items-baseline gap-x-(--km-space-5) gap-y-(--km-space-4) p-0",
        className,
      )}
    >
      {files.map(({ file, reason }) => (
        <li key={file} className="contents">
          <PathChip path={file} className="justify-self-start" />
          <span>{reason}</span>
        </li>
      ))}
    </ul>
  );
}
