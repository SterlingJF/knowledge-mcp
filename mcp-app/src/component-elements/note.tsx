// K06 Note: a quiet block for something you should know before deciding. Bold the fact, then the reason.
import { Ban, Info, TriangleAlert } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { action } from "@/copy/en";
import { cn } from "@/lib/utils";

import { LinkButton } from "./link-button";

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
        "flex items-start gap-km-gap-inline rounded-lg bg-muted p-km-pad-box text-xs leading-xs text-foreground",
        className,
      )}
    >
      <Icon aria-hidden className="mt-km-1 size-km-icon shrink-0" />
      <div className="min-w-0">
        {fact != null && <b className="font-semibold">{fact}</b>}
        {fact != null && children != null && " "}
        {children}
        {onShowWhy && (
          <>
            {" "}
            <LinkButton onClick={onShowWhy}>{action.showWhy}</LinkButton>
          </>
        )}
      </div>
    </div>
  );
}
