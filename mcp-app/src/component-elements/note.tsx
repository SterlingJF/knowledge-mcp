// K06 Note: a quiet block for something you should know before deciding. Bold the fact, then the reason.
import { Ban, Info, TriangleAlert } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { action } from "@/copy/en";
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
  onShowWhy,
  className,
}: {
  kind: NoteKind;
  fact?: ReactNode;
  children?: ReactNode;
  /** Adds the "Show why" disclosure after the reason. */
  onShowWhy?: () => void;
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
      <Icon
        aria-hidden
        className="mt-(--km-space-1) size-(--km-icon) shrink-0"
      />
      <div className="min-w-0">
        {fact != null && (
          <b className="font-(--font-weight-semibold)">{fact}</b>
        )}
        {fact != null && children != null && " "}
        {children}
        {onShowWhy && (
          <>
            {" "}
            <button
              type="button"
              onClick={onShowWhy}
              className="relative inline-flex cursor-pointer items-center gap-(--km-space-2) rounded-(--border-radius-xs) border-0 bg-transparent p-0 text-(length:--font-text-xs-size) text-(--color-text-primary) underline underline-offset-2 outline-none focus-visible:shadow-(--km-focus-ring) pointer-coarse:before:absolute pointer-coarse:before:top-1/2 pointer-coarse:before:left-1/2 pointer-coarse:before:size-(--km-target) pointer-coarse:before:-translate-1/2 pointer-coarse:before:content-['']"
            >
              {action.showWhy}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
