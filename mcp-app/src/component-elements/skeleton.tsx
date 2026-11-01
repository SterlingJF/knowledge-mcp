// K10 Skeleton: core Skeleton in the shape of the card that replaces it (header, rows, actions). No spinner.
import { Skeleton } from "@/component-core/skeleton";
import { status } from "@/copy/en";
import { cn } from "@/lib/utils";

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
      className={cn("flex w-full flex-col gap-4", className)}
    >
      <div className="flex flex-col gap-2">
        <Skeleton className="h-3 w-1/4" />
        <Skeleton className="h-5 w-3/5" />
      </div>
      <div className="flex flex-col gap-2">
        {Array.from({ length: rows }, (_, i) => (
          <Skeleton key={i} className="h-5 w-full" />
        ))}
      </div>
      {actions > 0 && (
        <div className="flex gap-2">
          {Array.from({ length: actions }, (_, i) => (
            <Skeleton key={i} className="h-9 w-24" />
          ))}
        </div>
      )}
    </div>
  );
}
