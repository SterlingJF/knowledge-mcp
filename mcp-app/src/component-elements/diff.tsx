// K09 Diff: the exact before and after of a saved edit. Removed lines are struck through so the meaning survives without colour.
import { cn } from "@/lib/utils";

export type DiffLine = { kind: "removed" | "added"; text: string };

export function Diff({
  lines,
  className,
}: {
  lines: readonly DiffLine[];
  className?: string;
}) {
  return (
    <div
      className={cn(
        "mt-km-gap-group overflow-hidden rounded-lg border-hairline border-solid border-border text-xs",
        className,
      )}
    >
      {lines.map((line, index) =>
        line.kind === "removed" ? (
          <del
            key={index}
            className="block bg-danger p-km-pad-line text-destructive line-through [overflow-wrap:anywhere]"
          >
            {line.text}
          </del>
        ) : (
          <ins
            key={index}
            className="block bg-success p-km-pad-line text-success no-underline [overflow-wrap:anywhere]"
          >
            {line.text}
          </ins>
        ),
      )}
    </div>
  );
}
