// K06 Note: core Alert for something you should know before deciding. The fact is the title, the reason
// the description. Info and left-out notes are notes, not alerts: only a warning interrupts.
import { Ban, Info, TriangleAlert } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/component-core/alert";

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
    <Alert
      role={kind === "warning" ? "alert" : "note"}
      data-kind={kind}
      variant={kind === "warning" ? "destructive" : "default"}
      className={className}
    >
      <Icon aria-hidden />
      {fact != null && <AlertTitle>{fact}</AlertTitle>}
      {children != null && <AlertDescription>{children}</AlertDescription>}
    </Alert>
  );
}
