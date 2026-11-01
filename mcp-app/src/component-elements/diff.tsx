// K09 Diff: the exact before and after of a saved edit. Each line starts with − or +, so the meaning
// survives without colour.
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
        "overflow-hidden rounded-lg border font-mono text-xs",
        className,
      )}
    >
      {lines.map((line, index) => {
        const removed = line.kind === "removed";
        const Line = removed ? "del" : "ins";
        return (
          <Line
            key={index}
            className={cn(
              "flex gap-2 px-3 py-1 no-underline",
              removed
                ? "bg-destructive/10 text-destructive"
                : "bg-success text-success-foreground",
            )}
          >
            <span aria-hidden="true" className="select-none">
              {removed ? "−" : "+"}
            </span>
            <span className="min-w-0 wrap-anywhere">{line.text}</span>
          </Line>
        );
      })}
    </div>
  );
}
