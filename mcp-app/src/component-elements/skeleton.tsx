// K10 Skeleton: loading in the shape of the card that replaces it (header, rows, actions). No spinner.
import { Skeleton as CoreSkeleton } from "@/component-core/skeleton";
import { status } from "@/copy/en";
import { cn } from "@/lib/utils";

const shapes = {
  line: "h-km-5",
  short: "h-km-5 w-2/5",
  title: "h-km-6 w-3/5",
  row: "h-km-row",
  action: "h-km-target w-1/4",
} as const;

export type SkeletonShape = keyof typeof shapes;

export function SkeletonBlock({
  shape = "line",
  className,
}: {
  shape?: SkeletonShape;
  className?: string;
}) {
  return (
    <CoreSkeleton
      aria-hidden
      className={cn(
        "mt-km-gap-row block rounded-lg bg-muted animate-km-shimmer motion-reduce:animate-none",
        shapes[shape],
        className,
      )}
    />
  );
}

export function CardSkeleton({
  rows = 3,
  actions = 0,
  label = status.loading,
  className,
}: {
  rows?: number;
  actions?: 0 | 1 | 2;
  label?: string;
  className?: string;
}) {
  return (
    <div
      role="status"
      aria-label={label}
      aria-busy
      className={cn("w-full", className)}
    >
      <SkeletonBlock shape="short" />
      <SkeletonBlock shape="title" />
      {Array.from({ length: rows }, (_, i) => (
        <SkeletonBlock key={i} shape="row" />
      ))}
      {actions > 0 && (
        <div className="flex gap-km-gap-inline">
          {Array.from({ length: actions }, (_, i) => (
            <SkeletonBlock key={i} shape="action" />
          ))}
        </div>
      )}
    </div>
  );
}
