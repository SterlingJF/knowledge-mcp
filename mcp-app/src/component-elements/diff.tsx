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
        "mt-[var(--km-gap-group)] overflow-hidden rounded-[var(--border-radius-lg)] border-[length:var(--border-width-regular)] border-solid border-[color:var(--color-border-tertiary)] text-[length:var(--font-text-xs-size)]",
        className,
      )}
    >
      {lines.map((line, index) =>
        line.kind === "removed" ? (
          <del
            key={index}
            className="block bg-[var(--color-background-danger)] px-[var(--km-space-5)] py-[var(--km-space-2)] text-[color:var(--color-text-danger)] line-through"
          >
            {line.text}
          </del>
        ) : (
          <ins
            key={index}
            className="block bg-[var(--color-background-success)] px-[var(--km-space-5)] py-[var(--km-space-2)] text-[color:var(--color-text-success)] no-underline"
          >
            {line.text}
          </ins>
        ),
      )}
    </div>
  );
}
